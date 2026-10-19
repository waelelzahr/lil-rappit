"""YouTube Shorts upload via the YouTube Data API (OAuth refresh token)."""
import json
import os
from pathlib import Path

import requests

from .common import CFG


def enabled() -> bool:
    return all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def _access_token() -> str:
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"YouTube login failed ({r.status_code}): {r.text[:300]}")
    return r.json()["access_token"]


def upload_short(video: Path, title: str, description: str) -> dict:
    tok = _access_token()
    yt = CFG.get("youtube", {})
    title = title.strip()[:90]
    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"[:100]
    meta = {
        "snippet": {
            "title": title,
            "description": description[:4900],
            "tags": ["lil rappit", "funny animals", "comedy", "ai comedy", "shorts"],
            "categoryId": "23",  # Comedy
        },
        "status": {
            "privacyStatus": yt.get("privacy", "private"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # AI-generated content disclosure
        },
    }
    data = video.read_bytes()
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))},
        data=json.dumps(meta), timeout=60)
    if init.status_code >= 400:
        raise RuntimeError(f"YouTube upload init failed ({init.status_code}): {init.text[:400]}")
    up = requests.put(init.headers["Location"], data=data, timeout=900,
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"})
    if up.status_code >= 400:
        raise RuntimeError(f"YouTube upload failed ({up.status_code}): {up.text[:400]}")
    vid = up.json()["id"]
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}",
            "privacy": up.json().get("status", {}).get("privacyStatus")}
