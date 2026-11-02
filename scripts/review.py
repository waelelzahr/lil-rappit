"""Runs every 30 min: checks Discord for ✅ / 🔁 reactions and replies on drafts.
✅ (or replying "ok") approves an item for its posting slot.
🔁 (or replying with a note) regenerates it.
Typing "status" in the channel lists this week's items."""
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rappit import concepts, discord, items, pipeline, quota  # noqa: E402
from rappit.common import CFG, OUT, TZ, classify, episode, load_state, log, save_state  # noqa: E402


def approve(state: dict, item_id: str):
    it = state["items"][item_id]
    if it["status"] != "pending":
        return
    it["status"] = "approved"
    log(f"approved {item_id}")
    discord.send_text(f"✅ Approved. Scheduled for {it['slot'][:16].replace('T', ' ')}.",
                      reply_to=it["message_id"])


def redo(state: dict, item_id: str, note: str | None, from_queue: bool = False):
    it = state["items"][item_id]
    if it["status"] != "pending":
        discord.send_text(f"`{item_id}` is already {it['status']}, so I left it as is.")
        return
    if it["redos"] >= CFG["limits"]["max_redos_per_item"]:
        if it.get("limit_notified") == it["message_id"]:
            return
        it["limit_notified"] = it["message_id"]
        discord.send_text("Redo limit reached for this one. Tap ✅ on the latest version, "
                          "or raise `max_redos_per_item` in config.yaml.",
                          reply_to=it["message_id"])
        it["status"] = "pending"
        return
    if it.get("redo_queued") and not from_queue:
        return  # already waiting for Google's daily reset
    version = it["redos"] + 2
    ep = episode(state, it["episode"])
    if not from_queue:
        discord.send_text("🔁 On it, regenerating…" + (f"\n> {note}" if note else ""),
                          reply_to=it["message_id"])
    try:
        built = items.build(f"{item_id}-v{version}", it["kind"], ep, note=note,
                            soft_idx=it.get("soft_idx", 0) + it["redos"] + 1, no=it.get("no"))
    except quota.QuotaExceeded:
        reset = quota.next_reset()
        it["redo_queued"] = {"note": note, "not_before": reset.isoformat()}
        discord.send_text(f"⏳ Google's daily video limit is used up. I'll make this redo "
                          f"after {reset:%a %H:%M}.", reply_to=it["message_id"])
        return
    it.pop("redo_queued", None)
    it["redos"] += 1
    if it.get("tease"):
        cap, _, tags = built["caption"].rpartition("\n\n")
        built["caption"] = f"{cap}\n{it['tease']}\n\n{tags}" if cap else built["caption"]
    path = Path(built["file"])
    it["message_id"] = discord.send_item(item_id, it["kind"], path,
                                         built["caption"], title=ep["title"], version=version)
    pipeline.send_script(built, it["message_id"])
    it.update(run_id=os.environ.get("GITHUB_RUN_ID"), relpath=str(path.relative_to(OUT)),
              caption=built["caption"], title=built["title"])


def send_pitch(state: dict, theme: str | None, reply_to: str):
    ideas = concepts.pitch(state, theme)
    lines = [f"**{i + 1}. {x.get('title', '')}** ({x.get('cast', '')})\n{x.get('setup', '')} → "
             f"{x.get('punchline', '')}\n> {x.get('rappit_line', '')} — *{x.get('english', '')}*"
             for i, x in enumerate(ideas)]
    msg = discord.send_text("🎤 **Pitch**" + (f" · {theme}" if theme else "") + "\n\n"
                            + "\n\n".join(lines)
                            + "\n\nReply with a number to make that clip (e.g. `2`), or `pitch` again.",
                            reply_to=reply_to)
    state["pitch"] = {"message_id": msg.get("id") if isinstance(msg, dict) else None, "ideas": ideas}


def make_from_pitch(state: dict, n: int, reply_to: str):
    from datetime import timedelta
    ideas = (state.get("pitch") or {}).get("ideas") or []
    if not 1 <= n <= len(ideas):
        discord.send_text("No pitch with that number. Type `pitch` for new ideas.", reply_to=reply_to)
        return
    x = ideas[n - 1]
    discord.send_text(f"🎬 Making **{x.get('title', '')}**… (about 5 minutes)", reply_to=reply_to)
    hint = (f"{x.get('title', '')}: {x.get('setup', '')} Punchline: {x.get('punchline', '')} "
            f"Rappit's key line: {x.get('rappit_line', '')} ({x.get('english', '')}). Cast: {x.get('cast', '')}")
    ep = concepts.write(state, hint=hint)
    now = datetime.now(TZ)
    ep["id"] += f"-{now:%Y-%m-%d-%H%M}"
    state.setdefault("custom_episodes", []).append(ep)
    concepts.remember(state, ep, now.strftime("%Y-%m-%d"))
    day = now + timedelta(days=1) if now.hour >= 16 else now
    at = f"{day:%A} 18:00"
    from rappit.common import next_slot
    pipeline.make(state, ep["id"], "reel", ep, next_slot(at), 0, at)
    state.pop("pitch", None)


def add_idea(state: dict, idea: str, reply_to: str):
    """A viewer's suggestion becomes one of next week's clips (the writer builds around it)."""
    state.setdefault("concept_ideas", []).append(idea)
    discord.send_text(f"💡 Added: *{idea}*\nIt will be one of next week's clips.", reply_to=reply_to)


def status(state: dict):
    pending = {k: v for k, v in state["items"].items()
               if v["status"] in ("pending", "approved", "queued")}
    if not pending:
        discord.send_text("Nothing in the queue right now. New drafts arrive Sunday morning.")
        return
    icon = {"pending": "👀", "approved": "✅", "queued": "🗓️"}
    lines = [f"{icon[v['status']]} `{k}` · {v['status']} · {v['slot'][:16].replace('T', ' ')}"
             for k, v in sorted(pending.items())]
    discord.send_text("**Queue**\n" + "\n".join(lines)
                      + f"\nVeo videos left today: {quota.left()}")


def main():
    state = load_state()
    quota.bind(state)
    me = discord.bot_id()

    # 0) Work that was waiting for a scheduled time or Google's daily reset
    try:
        pipeline.run_queued(state, save_state)
        now = datetime.now(TZ)
        for item_id, it in list(state["items"].items()):
            q = it.get("redo_queued")
            if it["status"] == "pending" and q and datetime.fromisoformat(q["not_before"]) <= now:
                redo(state, item_id, q.get("note"), from_queue=True)
                save_state(state)
    except Exception as e:
        log(f"queued work failed: {e}\n{traceback.format_exc()}")
        discord.send_text(f"⚠️ Queued work failed: {str(e)[:300]}")
    save_state(state)

    # 1) Reactions on the current version of each pending draft
    for item_id, it in list(state["items"].items()):
        if it["status"] != "pending" or not it.get("message_id"):
            continue
        try:
            if discord.reacted(it["message_id"], discord.APPROVE):
                approve(state, item_id)
            elif discord.reacted(it["message_id"], discord.REDO):
                redo(state, item_id, None)
        except Exception as e:
            log(f"{item_id} failed: {e}\n{traceback.format_exc()}")
            discord.send_text(f"⚠️ Something failed on `{item_id}`: {e}")
        save_state(state)

    # 1b) Nothing in the pipeline? Pitch the next ideas automatically (max once a day, daytime)
    try:
        busy = any(v["status"] in ("pending", "approved", "queued") for v in state["items"].values())
        last = state.get("auto_pitch_at")
        now = datetime.now(TZ)
        recent = last and (now - datetime.fromisoformat(last)).total_seconds() < 20 * 3600
        if not busy and not state.get("pitch") and not recent and 9 <= now.hour < 22:
            send_pitch(state, None, None)
            state["auto_pitch_at"] = now.isoformat()
            save_state(state)
    except Exception as e:
        log(f"auto pitch failed: {e}")

    # 2) Text messages: replies to drafts, or commands
    msg_to_item = {it.get("message_id"): k for k, it in state["items"].items()}
    for m in discord.new_replies(state.get("discord_last")):
        state["discord_last"] = m["id"]
        save_state(state)  # never handle the same message twice
        if m["author"]["id"] == me or m["author"].get("bot"):
            continue
        text = (m.get("content") or "").strip()
        ref = (m.get("message_reference") or {}).get("message_id")
        try:
            if ref in msg_to_item and text.lower().strip(" !.") in ("post now", "now", "post it now"):
                item_id = msg_to_item[ref]
                state["items"][item_id]["slot"] = datetime.now(TZ).isoformat()
                if state["items"][item_id]["status"] == "pending":
                    state["items"][item_id]["status"] = "approved"
                discord.send_text("🚀 Posting this now…", reply_to=state["items"][item_id]["message_id"])
            elif ref in msg_to_item:
                item_id = msg_to_item[ref]
                action, note = classify(text)
                if action == "approve":
                    approve(state, item_id)
                else:
                    redo(state, item_id, note)
            elif text.lower() == "token updated":
                state.pop("ig_token_warned", None)
                state.pop("ig_token_seen", None)
                discord.send_text("👍 Thanks, I'll remind you again in 50 days.")
            elif text.lower().startswith("pitch"):
                send_pitch(state, text[5:].strip(" :-") or None, m["id"])
            elif text.strip().isdigit() and state.get("pitch"):
                make_from_pitch(state, int(text.strip()), m["id"])
            elif text.lower().startswith("idea"):
                idea = text[4:].strip(" :-")
                if idea:
                    add_idea(state, idea, m["id"])
                else:
                    discord.send_text("Write it like: `idea Rappit tries to get a refund at IKEA`")
            elif text.lower() in ("status", "queue", "list"):
                status(state)
            elif text:
                discord.send_text("To change a draft, **reply** to it with your note "
                                  "(long-press → Reply), or reply `post now` to publish it right away. "
                                  "Type `pitch` (or `pitch weddings`) for clip ideas, `status` for the queue.")
        except Exception as e:
            log(f"message {m['id']} failed: {e}\n{traceback.format_exc()}")
            discord.send_text(f"⚠️ Something failed: {e}")
        save_state(state)
        msg_to_item = {it.get("message_id"): k for k, it in state["items"].items()}


if __name__ == "__main__":
    main()
