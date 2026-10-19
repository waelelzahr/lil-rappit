"""Prints which YouTube channel the saved login points to (no upload)."""
import sys
import traceback
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import discord, youtube  # noqa: E402

try:
    tok = youtube._access_token()
    r = requests.get("https://www.googleapis.com/youtube/v3/channels",
                     params={"part": "snippet", "mine": "true"},
                     headers={"Authorization": f"Bearer {tok}"}, timeout=60).json()
    items = r.get("items", [])
    if not items:
        msg = f"⚠️ This YouTube login has no channel attached: {str(r)[:300]}"
    else:
        ch = items[0]
        msg = (f"📺 YouTube is connected to **{ch['snippet']['title']}** "
               f"(https://youtube.com/channel/{ch['id']})")
except Exception as e:
    msg = f"⚠️ YouTube check failed: {str(e)[:400]}"
    traceback.print_exc()
print(f"::notice::{msg}")
try:
    discord.send_text(msg)
except Exception as e:
    print(f"::warning::Discord send failed: {e}")
