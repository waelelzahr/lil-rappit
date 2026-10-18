"""Discord review channel (REST only, no always-on server needed).

The bot posts each draft in your private channel and adds ✅ and 🔁 reactions.
Tap ✅ to approve, 🔁 to regenerate, or reply to the draft with a note to
regenerate using your note.
"""
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests

API = "https://discord.com/api/v10"
APPROVE, REDO = "✅", "🔁"
MAX_UPLOAD = 9_500_000  # Discord's 10 MB limit for bots, with margin


def _h():
    return {
        "Authorization": f"Bot {os.environ['DISCORD_BOT_TOKEN']}",
        "User-Agent": "DiscordBot (https://github.com/waelelzahr/lil-rappit, 1.0)",
    }


def _ch():
    return os.environ["DISCORD_CHANNEL_ID"]


def _req(method: str, path: str, **kw):
    import time
    for _ in range(5):
        r = requests.request(method, API + path, headers=_h(), timeout=120, **kw)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 1)) + 0.2)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Discord {method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else None
    raise RuntimeError("Discord rate limit retries exhausted")


def _preview(path: Path) -> Path:
    """Discord caps bot uploads at ~10 MB; shrink the preview if needed.
    The full-quality file is kept separately for posting."""
    if path.stat().st_size <= MAX_UPLOAD or path.suffix != ".mp4":
        return path
    small = path.with_name(path.stem + "_preview.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path),
                    "-vf", "scale=720:-2", "-c:v", "libx264", "-b:v", "2500k",
                    "-maxrate", "3000k", "-bufsize", "6000k", "-c:a", "aac", "-b:a", "96k",
                    "-movflags", "+faststart", str(small)], check=True)
    return small


def bot_id() -> str:
    return _req("GET", "/users/@me")["id"]


def send_item(item_id: str, kind: str, path: Path, caption: str, title: str = "",
              version: int = 1) -> str:
    label = {"reel": "🎬 Reel", "mugshot": "📸 Mugshot", "soft": "🥕 Soft side"}[kind]
    v = f" (v{version})" if version > 1 else ""
    content = (f"**{label}{v}** · {title}\n`{item_id}`\n\n{caption}\n\n"
               f"{APPROVE} approve · {REDO} redo · or reply with what to change")[:2000]
    p = _preview(path)
    with open(p, "rb") as f:
        msg = _req("POST", f"/channels/{_ch()}/messages",
                   data={"payload_json": json.dumps({"content": content})},
                   files={"files[0]": (p.name, f)})
    for emoji in (APPROVE, REDO):
        _req("PUT", f"/channels/{_ch()}/messages/{msg['id']}/reactions/{quote(emoji)}/@me")
    return msg["id"]


def send_text(text: str, reply_to: str | None = None):
    body = {"content": text[:2000]}
    if reply_to:
        body["message_reference"] = {"message_id": reply_to, "fail_if_not_exists": False}
    return _req("POST", f"/channels/{_ch()}/messages", json=body)


def reacted(message_id: str, emoji: str) -> bool:
    """True if a human (not the bot) reacted with emoji."""
    try:
        users = _req("GET", f"/channels/{_ch()}/messages/{message_id}/reactions/{quote(emoji)}",
                     params={"limit": 100})
    except RuntimeError:
        return False
    return any(not u.get("bot") for u in users or [])


def new_replies(after_id: str | None) -> list[dict]:
    """Human messages in the channel after after_id (oldest first)."""
    params = {"limit": 100}
    if after_id:
        params["after"] = after_id
    msgs = _req("GET", f"/channels/{_ch()}/messages", params=params) or []
    msgs.sort(key=lambda m: int(m["id"]))
    return msgs
