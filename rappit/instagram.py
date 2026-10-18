"""Instagram publishing via the Instagram API with Instagram Login.

Reels are uploaded directly (resumable upload, no public URL needed).
Photos must be JPEG at a public URL, so we briefly host them as a Discord
attachment (the CDN link is public) and hand that URL to Instagram.
"""
import os
import subprocess
import time
from pathlib import Path

import requests

GRAPH = "https://graph.instagram.com/v23.0"


def _tok():
    return os.environ["IG_ACCESS_TOKEN"]


def _uid():
    return os.environ["IG_USER_ID"]


def _check(r: requests.Response) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:300]}
    if r.status_code >= 400 or "error" in body:
        raise RuntimeError(f"Instagram {r.request.method} {r.url.split('?')[0]} -> "
                           f"{r.status_code}: {body.get('error', body)}")
    return body


def _wait_ready(container_id: str, timeout: int = 600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = _check(requests.get(f"{GRAPH}/{container_id}",
                                 params={"fields": "status_code,status", "access_token": _tok()},
                                 timeout=60))
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram processing failed: {st.get('status')}")
        time.sleep(10)
    raise TimeoutError("Instagram took too long to process the media")


def _publish(container_id: str) -> dict:
    res = _check(requests.post(f"{GRAPH}/{_uid()}/media_publish",
                               data={"creation_id": container_id, "access_token": _tok()},
                               timeout=120))
    media_id = res["id"]
    info = _check(requests.get(f"{GRAPH}/{media_id}",
                               params={"fields": "permalink", "access_token": _tok()}, timeout=60))
    return {"id": media_id, "url": info.get("permalink", "")}


def post_reel(video: Path, caption: str) -> dict:
    c = _check(requests.post(f"{GRAPH}/{_uid()}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": "true", "access_token": _tok()}, timeout=60))
    data = video.read_bytes()
    up = requests.post(c["uri"], data=data, timeout=600, headers={
        "Authorization": f"OAuth {_tok()}", "offset": "0", "file_size": str(len(data))})
    _check(up)
    _wait_ready(c["id"])
    return _publish(c["id"])


def to_feed_jpeg(img: Path) -> Path:
    """Instagram feed photos must be JPEG with aspect between 4:5 and 1.91:1."""
    out = img.with_name(img.stem + "_ig.jpg")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(img), "-vf",
                    "crop='min(iw,ih*1.91)':'min(ih,iw*5/4)',scale='min(1440,iw)':-2",
                    "-q:v", "2", str(out)], check=True)
    return out


def post_photo(image_url: str, caption: str) -> dict:
    c = _check(requests.post(f"{GRAPH}/{_uid()}/media", data={
        "image_url": image_url, "caption": caption, "access_token": _tok()}, timeout=120))
    _wait_ready(c["id"], timeout=300)
    return _publish(c["id"])


def refresh_token() -> str | None:
    """Extend the long-lived token (valid 60 days). Returns new token or None."""
    try:
        r = _check(requests.get("https://graph.instagram.com/refresh_access_token",
                                params={"grant_type": "ig_refresh_token", "access_token": _tok()},
                                timeout=60))
        return r.get("access_token")
    except Exception:
        return None
