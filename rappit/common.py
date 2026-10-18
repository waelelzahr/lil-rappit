import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
EPISODES = yaml.safe_load((ROOT / "episodes.yaml").read_text(encoding="utf-8"))
STATE_FILE = ROOT / "state" / "state.json"
OUT = Path(os.environ.get("OUT_DIR", ROOT / "out"))
TZ = ZoneInfo("Asia/Beirut")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def log(msg: str):
    print(f"[{datetime.now(TZ):%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"used_episodes": [], "items": {}, "tg_offset": 0}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def next_slot(spec: str, now: datetime | None = None) -> str:
    """'Monday 18:00' -> ISO datetime of the next such moment (Beirut time)."""
    now = now or datetime.now(TZ)
    day, hm = spec.split()
    h, m = map(int, hm.split(":"))
    delta = (DAYS.index(day) - now.weekday()) % 7
    when = (now + timedelta(days=delta)).replace(hour=h, minute=m, second=0, microsecond=0)
    if when <= now:
        when += timedelta(days=7)
    return when.isoformat()
