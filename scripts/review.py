"""Hourly job: read Telegram replies. Approve marks an item ready to post;
Redo (button or a text reply to a draft) regenerates it."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rappit import items, telegram  # noqa: E402
from rappit.common import CFG, EPISODES, OUT, load_state, log, save_state  # noqa: E402

EP_BY_ID = {e["id"]: e for e in EPISODES}


def redo(state: dict, item_id: str, note: str | None):
    it = state["items"][item_id]
    if it["status"] in ("approved", "posted"):
        telegram.send_text(f"{item_id} is already {it['status']}.")
        return
    if it["redos"] >= CFG["limits"]["max_redos_per_item"]:
        telegram.send_text(f"Redo limit reached for {item_id}. Approve it or edit "
                           "max_redos_per_item in config.yaml.")
        return
    telegram.clear_buttons(it["message_id"])
    telegram.send_text(f"🔁 Regenerating {item_id}…" + (f"\nNote: {note}" if note else ""))
    it["redos"] += 1
    new_id = f"{item_id}-v{it['redos'] + 1}"
    built = items.build(new_id, it["kind"], EP_BY_ID[it["episode"]], note=note,
                        soft_idx=it.get("soft_idx", 0) + it["redos"])
    path = Path(built["file"])
    it["message_id"] = telegram.send_item(
        item_id, it["kind"], path,
        f"[{it['kind'].upper()} v{it['redos'] + 1}]\n\n{built['caption']}")
    it.update(run_id=os.environ.get("GITHUB_RUN_ID"), relpath=str(path.relative_to(OUT)),
              caption=built["caption"], title=built["title"], status="pending")


def main():
    state = load_state()
    msg_to_item = {it["message_id"]: iid for iid, it in state["items"].items()}
    ups = telegram.updates(state.get("tg_offset", 0))
    allowed_chat = str(telegram.chat_id())

    for u in ups:
        state["tg_offset"] = u["update_id"] + 1
        save_state(state)  # never process the same update twice
        cb = u.get("callback_query")
        msg = u.get("message")
        try:
            if cb and str(cb["message"]["chat"]["id"]) == allowed_chat:
                action, item_id = cb["data"].split(":", 1)
                if item_id not in state["items"]:
                    continue
                if action == "approve":
                    it = state["items"][item_id]
                    it["status"] = "approved"
                    telegram.answer(cb["id"], "Approved ✅")
                    telegram.clear_buttons(it["message_id"])
                    telegram.send_text(f"✅ {item_id} approved, posts {it['slot'][:16]}.",
                                       reply_to=it["message_id"])
                elif action == "redo":
                    telegram.answer(cb["id"], "Regenerating…")
                    redo(state, item_id, None)
            elif msg and str(msg["chat"]["id"]) == allowed_chat:
                reply_to = (msg.get("reply_to_message") or {}).get("message_id")
                if reply_to in msg_to_item:
                    redo(state, msg_to_item[reply_to], msg.get("text"))
        except Exception as e:
            log(f"update {u['update_id']} failed: {e}")
            telegram.send_text(f"⚠️ Something failed: {e}")
        save_state(state)
        msg_to_item = {it["message_id"]: iid for iid, it in state["items"].items()}


if __name__ == "__main__":
    main()
