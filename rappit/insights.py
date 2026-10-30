"""How our own posts performed (best effort; needs the insights permissions on the tokens)."""
import requests

from . import instagram, youtube
from .common import log

IG_METRICS = "views,reach,likes,comments,shares,saved,total_interactions,ig_reels_avg_watch_time"


def instagram_posts(limit: int = 20) -> list[dict]:
    g, tok = instagram.GRAPH, instagram._tok()
    media = requests.get(f"{g}/{instagram._uid()}/media", params={
        "fields": "id,permalink,caption,timestamp,media_type", "limit": limit,
        "access_token": tok}, timeout=60).json().get("data", [])
    out = []
    for m in media:
        row = {"url": m.get("permalink"), "when": m.get("timestamp", "")[:10],
               "caption": (m.get("caption") or "").split("\n")[0][:120], "type": m.get("media_type")}
        r = requests.get(f"{g}/{m['id']}/insights",
                         params={"metric": IG_METRICS, "access_token": tok}, timeout=60).json()
        if "error" in r:  # photos don't support some metrics; retry with the basic set
            r = requests.get(f"{g}/{m['id']}/insights", params={
                "metric": "reach,likes,comments,shares,saved", "access_token": tok}, timeout=60).json()
        for d in r.get("data", []):
            row[d["name"]] = (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value"))
        if "error" in r:
            row["error"] = r["error"].get("message", "")[:120]
        out.append(row)
    return out


def youtube_posts(limit: int = 20) -> list[dict]:
    h = {"Authorization": f"Bearer {youtube._access_token()}"}
    api = "https://www.googleapis.com/youtube/v3"
    ch = requests.get(f"{api}/channels", params={"part": "contentDetails", "mine": "true"},
                      headers=h, timeout=60).json()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = requests.get(f"{api}/playlistItems", params={
        "part": "contentDetails", "playlistId": uploads, "maxResults": limit},
        headers=h, timeout=60).json().get("items", [])
    ids = ",".join(i["contentDetails"]["videoId"] for i in items)
    vids = requests.get(f"{api}/videos", params={"part": "snippet,statistics", "id": ids},
                        headers=h, timeout=60).json().get("items", []) if ids else []
    return [{"title": v["snippet"]["title"][:100], "when": v["snippet"]["publishedAt"][:10],
             **{k: int(x) for k, x in v.get("statistics", {}).items() if x.isdigit()}} for v in vids]


def summary() -> str:
    """Plain-text performance table for the writer (and for you in Discord)."""
    parts = []
    try:
        rows = instagram_posts()
        parts.append("INSTAGRAM (newest first):\n" + "\n".join(
            f"- {r['when']} {r.get('type', '')}: views={r.get('views', '?')} reach={r.get('reach', '?')} "
            f"likes={r.get('likes', '?')} comments={r.get('comments', '?')} shares={r.get('shares', '?')} "
            f"saves={r.get('saved', '?')} avg_watch_ms={r.get('ig_reels_avg_watch_time', '?')} | {r['caption']}"
            + (f" [{r['error']}]" if r.get("error") else "") for r in rows))
    except Exception as e:
        log(f"instagram insights unavailable: {e}")
        parts.append(f"INSTAGRAM: stats unavailable ({str(e)[:120]})")
    try:
        if youtube.enabled():
            rows = youtube_posts()
            parts.append("YOUTUBE (newest first):\n" + "\n".join(
                f"- {r['when']}: views={r.get('viewCount', 0)} likes={r.get('likeCount', 0)} "
                f"comments={r.get('commentCount', 0)} | {r['title']}" for r in rows))
    except Exception as e:
        log(f"youtube stats unavailable: {e}")
        parts.append(f"YOUTUBE: stats unavailable ({str(e)[:120]})")
    return "\n\n".join(parts)
