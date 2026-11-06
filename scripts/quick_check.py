"""Fast pre-check (standard library only, a few seconds): is there anything for the review
job to do? Prints work=true/false for GitHub Actions. Any error -> work=true (safe side)."""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://discord.com/api/v10"


def discord(path: str, params: dict | None = None):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bot {os.environ['DISCORD_BOT_TOKEN']}",
        "User-Agent": "rappit-quick-check (https://github.com, 1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def other_runs_busy() -> bool:
    """True if another workflow run of this repo is running or waiting (then we step aside, so
    we never bump a waiting video job out of the queue)."""
    repo, me = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")
    if not repo:
        return False
    for status in ("in_progress", "queued", "waiting", "pending"):
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/actions/runs?status={status}&per_page=20",
            headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                     "Accept": "application/vnd.github+json", "User-Agent": "rappit"})
        with urllib.request.urlopen(req, timeout=30) as r:
            runs = json.loads(r.read()).get("workflow_runs", [])
        now = datetime.now(timezone.utc)
        if any(str(x["id"]) != me and (now - datetime.fromisoformat(
                x["created_at"].replace("Z", "+00:00"))).total_seconds() < 2 * 3600 for x in runs):
            return True  # ignore stale runs stuck for hours
    return False


def reasons() -> list[str]:
    if other_runs_busy():
        return []  # try again in 5 minutes
    state = json.loads((ROOT / "state" / "state.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    if now.hour == 9 and now.minute < 5:  # one full run a day (token reminders, housekeeping)
        return ["daily full run"]
    out = ["retry a picked clip"] if state.get("retry_pick") else []
    for k, it in state.get("items", {}).items():
        st = it.get("status")
        if st == "queued" and datetime.fromisoformat(it["not_before"]) <= now:
            out.append(f"{k} queued and due")
        if st == "approved" and datetime.fromisoformat(it["slot"]) <= now:
            out.append(f"{k} due to post")
        q = it.get("redo_queued")
        if st == "pending" and q and datetime.fromisoformat(q["not_before"]) <= now:
            out.append(f"{k} redo due")
    busy = any(v.get("status") in ("pending", "approved", "queued") for v in state.get("items", {}).values())
    last = state.get("auto_pitch_at")
    local_hour = (now.hour + 2) % 24  # Beirut (close enough for a daytime window)
    if not busy and not state.get("pitch") and 9 <= local_hour < 22 and (
            not last or (now - datetime.fromisoformat(last)).total_seconds() > 20 * 3600):
        out.append("time for an automatic pitch")
    ch = os.environ["DISCORD_CHANNEL_ID"]
    params = {"limit": 50}
    if state.get("discord_last"):
        params["after"] = state["discord_last"]
    if any(not (m.get("author") or {}).get("bot") for m in discord(f"/channels/{ch}/messages", params) or []):
        out.append("new message")
    for k, it in state.get("items", {}).items():
        if it.get("status") == "pending" and it.get("message_id"):
            msg = discord(f"/channels/{ch}/messages/{it['message_id']}")
            for r in msg.get("reactions") or []:
                if r.get("count", 0) > (1 if r.get("me") else 0):
                    out.append(f"{k} reacted")
    return out


if __name__ == "__main__":
    try:
        why = reasons()
    except Exception as e:  # never miss work because the pre-check broke
        why = [f"pre-check error: {e}"]
    print(f"work={'true' if why else 'false'}")
    print("; ".join(why) or "nothing to do", file=sys.stderr)
