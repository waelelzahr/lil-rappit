"""Publishes approved items whose posting slot has arrived (runs after review)."""
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rappit import discord, instagram, media  # noqa: E402
from rappit.common import TZ, load_state, log, save_state  # noqa: E402

MAX_ATTEMPTS = 3


def post_item(it: dict) -> str:
    path = media.fetch(it["run_id"], it["relpath"])
    # Host an Instagram-ready copy on Discord's public CDN so Instagram can fetch it.
    ready = instagram.to_reel_upload(path) if it["kind"] == "reel" else instagram.to_feed_jpeg(path)
    msg = discord.send_file(ready, "📤 Uploading to Instagram…", reply_to=it.get("message_id"))
    url = msg["attachments"][0]["url"]
    if it["kind"] == "reel":
        res = instagram.post_reel(url, it["caption"])
    else:
        res = instagram.post_photo(url, it["caption"])
    return res["url"]


def main():
    if not os.environ.get("IG_ACCESS_TOKEN"):
        log("IG_ACCESS_TOKEN not set; skipping posting")
        return
    state = load_state()
    now = datetime.now(TZ)
    for item_id, it in sorted(state["items"].items(), key=lambda kv: kv[1]["slot"]):
        if it["status"] != "approved" or datetime.fromisoformat(it["slot"]) > now:
            continue
        try:
            url = post_item(it)
            it.update(status="posted", posted_at=now.isoformat(), instagram=url)
            log(f"posted {item_id}: {url}")
            discord.send_text(f"🚀 Posted on Instagram: {url}", reply_to=it.get("message_id"))
        except Exception as e:
            it["attempts"] = it.get("attempts", 0) + 1
            log(f"post {item_id} failed: {e}\n{traceback.format_exc()}")
            if it["attempts"] >= MAX_ATTEMPTS:
                it["status"] = "failed"
                discord.send_text(f"❌ Couldn't post `{item_id}` after {MAX_ATTEMPTS} tries: {e}",
                                  reply_to=it.get("message_id"))
            else:
                discord.send_text(f"⚠️ Posting `{item_id}` failed, will retry: {str(e)[:300]}",
                                  reply_to=it.get("message_id"))
        save_state(state)

    # Keep the Instagram token alive: warn 10 days before its 60-day expiry.
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
