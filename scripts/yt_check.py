"""Prints which YouTube channel the saved login points to (no upload)."""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import discord, youtube  # noqa: E402

tok = youtube._access_token()
r = requests.get("https://www.googleapis.com/youtube/v3/channels",
                 params={"part": "snippet,statistics", "mine": "true"},
                 headers={"Authorization": f"Bearer {tok}"}, timeout=60).json()
items = r.get("items", [])
if not items:
    msg = f"⚠️ This YouTube login has no channel attached: {r}"
else:
    ch = items[0]
    msg = (f"📺 YouTube is connected to **{ch['snippet']['title']}** "
           f"(https://youtube.com/channel/{ch['id']}), "
           f"{ch['statistics'].get('subscriberCount', '?')} subscribers.")
print(msg)
discord.send_text(msg)
