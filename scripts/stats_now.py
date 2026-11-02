"""Write current Instagram + YouTube stats to state/stats.md (no research, no cost)."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import insights  # noqa: E402
from rappit.common import ROOT, TZ  # noqa: E402

def profile() -> str:
    import requests
    from rappit import instagram
    r = requests.get(f"{instagram.GRAPH}/me", params={
        "fields": "username,name,biography,website,followers_count,follows_count,media_count",
        "access_token": instagram._tok()}, timeout=60).json()
    return "PROFILE:\n" + "\n".join(f"- {k}: {v}" for k, v in r.items() if k != "id")


if __name__ == "__main__":
    try:
        prof = profile()
    except Exception as e:
        prof = f"PROFILE: unavailable ({e})"
    text = prof + "\n\n" + insights.summary()
    (ROOT / "state" / "stats.md").write_text(
        f"# Stats {datetime.now(TZ):%Y-%m-%d %H:%M}\n\n{text}\n", encoding="utf-8")
    print(text)
