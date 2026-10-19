"""Publishes approved items whose posting slot has arrived (runs after review)."""
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rappit import discord, instagram, media, youtube  # noqa: E402
from rappit.common import TZ, load_state, log, save_state  # noqa: E402

MAX_ATTEMPTS = 3
LABEL = {"instagram": "Instagram", "youtube": "YouTube"}


def to_instagram(it: dict, path: Path) -> str:
    # Host an Instagram-ready copy on Discord's public CDN so Instagram can fetch it.
    ready = instagram.to_reel_upload(path) if it["kind"] == "reel" else instagram.to_feed_jpeg(path)
    msg = discord.send_file(ready, "📤 Uploading to Instagram…", reply_to=it.get("message_id"))
    url = msg["attachments"][0]["url"]
    if it["kind"] == "reel":
        return instagram.post_reel(url, it["caption"])["url"]
    return instagram.post_photo(url, it["caption"])["url"]


def to_youtube(it: dict, path: Path) -> str:
    res = youtube.upload_short(path, it.get("title") or "Lil Rappit", it["caption"])
    note = " (private until the YouTube API audit is approved)" if res["privacy"] == "private" else ""
    return res["url"] + note


def platforms(it: dict) -> list[tuple[str, callable]]:
    out = []
    if os.environ.get("IG_ACCESS_TOKEN"):
        out.append(("instagram", to_instagram))
    if it["kind"] == "reel" and youtube.enabled():
        out.append(("youtube", to_youtube))
    return out


def main():
    state = load_state()
    now = datetime.now(TZ)
    for item_id, it in sorted(state["items"].items(), key=lambda kv: kv[1]["slot"]):
        if it["status"] != "approved" or datetime.fromisoformat(it["slot"]) > now:
            continue
        todo = [(name, fn) for name, fn in platforms(it) if not it.get(name)]
        if not todo:
            continue
        failed = []
        path = None
        for name, fn in todo:
            try:
                path = path or media.fetch(it["run_id"], it["relpath"])
                url = fn(it, path)
                it[name] = url
                log(f"posted {item_id} to {name}: {url}")
                discord.send_text(f"🚀 Posted on {LABEL[name]}: {url}", reply_to=it.get("message_id"))
            except Exception as e:
                failed.append(f"{name}: {str(e)[:300]}")
                log(f"post {item_id} to {name} failed: {e}\n{traceback.format_exc()}")
            save_state(state)
        if not failed:
            it.update(status="posted", posted_at=now.isoformat())
        else:
            it["attempts"] = it.get("attempts", 0) + 1
            if it["attempts"] >= MAX_ATTEMPTS:
                it["status"] = "posted" if any(it.get(n) for n, _ in platforms(it)) else "failed"
                discord.send_text(f"❌ Gave up on `{item_id}` after {MAX_ATTEMPTS} tries:\n"
                                  + "\n".join(failed), reply_to=it.get("message_id"))
            else:
                discord.send_text(f"⚠️ Posting `{item_id}` failed, will retry:\n" + "\n".join(failed),
                                  reply_to=it.get("message_id"))
        save_state(state)

    # Keep the Instagram token alive: warn 10 days before its 60-day expiry.
    if not os.environ.get("IG_ACCESS_TOKEN"):
        return
    first = state.setdefault("ig_token_seen", now.isoformat())
    age = (now - datetime.fromisoformat(first)).days
    if age >= 50 and not state.get("ig_token_warned"):
        discord.send_text("🔑 The Instagram token expires in about 10 days. Generate a new one "
                          "in the Meta dashboard and update the IG_ACCESS_TOKEN secret on GitHub, "
                          "then type `token updated` here.")
        state["ig_token_warned"] = True
    save_state(state)


if __name__ == "__main__":
    main()
