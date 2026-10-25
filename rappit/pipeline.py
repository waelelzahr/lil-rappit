"""Shared: build an item, send it to Discord, record it; queue it if Veo's limit is hit."""
import os
from datetime import datetime
from pathlib import Path

from . import discord, items, quota
from .common import OUT, TZ, episode, log


def _when(dt) -> str:
    return dt.strftime("%a %H:%M")


def queue(state: dict, item_id: str, kind: str, ep: dict, slot: str, soft_idx: int,
          not_before: datetime, reason: str, tease: str = ""):
    state["items"][item_id] = {
        "kind": kind, "episode": ep["id"], "slot": slot, "status": "queued",
        "not_before": not_before.isoformat(), "redos": 0, "soft_idx": soft_idx, "tease": tease}
    log(f"queued {item_id} until {not_before:%Y-%m-%d %H:%M}: {reason}")


def make(state: dict, item_id: str, kind: str, ep: dict, slot: str, soft_idx: int,
         label_when: str, tease: str = "") -> None:
    """Build + send a draft. On QuotaExceeded, queue it for after Google's reset."""
    no = None
    if kind == "reel":  # episode counter shown as "DAY n"; test drafts don't advance it
        no = state.get("episode_no", 4) + 1
        if not item_id.startswith("test"):
            state["episode_no"] = no
    try:
        built = items.build(item_id, kind, ep, soft_idx=soft_idx, no=no)
    except quota.QuotaExceeded as e:
        if no and not item_id.startswith("test"):
            state["episode_no"] = no - 1  # not made yet; give the number back
        reset = quota.next_reset()
        queue(state, item_id, kind, ep, slot, soft_idx, reset, str(e), tease)
        discord.send_text(f"⏳ Google's daily video limit is used up, so **{ep['title']}** "
                          f"({kind}) will be made after {_when(reset)}.")
        return
    except Exception:
        if no and not item_id.startswith("test"):
            state["episode_no"] = no - 1  # failed; the retry reuses this number
        raise
    if tease:  # a reason to follow: what's next
        cap, _, tags = built["caption"].rpartition("\n\n")
        built["caption"] = f"{cap}\n{tease}\n\n{tags}" if cap else f"{built['caption']}\n{tease}"
    path = Path(built["file"])
    msg_id = discord.send_item(item_id, kind, path, f"Posts: {label_when}\n\n{built['caption']}",
                               title=ep["title"])
    send_script(built, msg_id)
    state["items"][item_id] = {
        "kind": kind, "episode": ep["id"], "slot": slot, "status": "pending", "redos": 0,
        "message_id": msg_id, "run_id": os.environ.get("GITHUB_RUN_ID"),
        "relpath": str(path.relative_to(OUT)), "caption": built["caption"],
        "title": built["title"], "soft_idx": soft_idx, "tease": tease, "no": no}


def send_script(built: dict, msg_id: str) -> None:
    """Post the reel's script as a reply under its draft (never fatal)."""
    text = built.get("script_text")
    if not text:
        return
    try:
        chunk = ""
        for line in text.split("\n"):
            if len(chunk) + len(line) > 1900:
                discord.send_text(chunk, reply_to=msg_id)
                chunk = ""
            chunk += line + "\n"
        if chunk.strip():
            discord.send_text(chunk, reply_to=msg_id)
    except Exception as e:
        log(f"could not post script: {e}")


def run_queued(state: dict, save) -> None:
    """Build queued items whose time has come (called by the 30-min job)."""
    now = datetime.now(TZ)
    for item_id, it in sorted(state["items"].items()):
        if it["status"] != "queued" or datetime.fromisoformat(it["not_before"]) > now:
            continue
        ep = episode(state, it["episode"])
        slot_dt = datetime.fromisoformat(it["slot"])
        make(state, item_id, it["kind"], ep, it["slot"], it.get("soft_idx", 0),
             slot_dt.strftime("%A %H:%M"), it.get("tease", ""))
        save(state)
