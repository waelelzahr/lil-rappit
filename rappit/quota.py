"""Tracks Veo's daily request limit (resets at midnight US Pacific) in state.json."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .common import CFG, TZ

PT = ZoneInfo("America/Los_Angeles")
_state: dict | None = None


class QuotaExceeded(Exception):
    """Not enough Veo requests left today."""


def bind(state: dict):
    global _state
    _state = state


def _today() -> str:
    return datetime.now(PT).strftime("%Y-%m-%d")


def _usage() -> dict:
    u = _state.setdefault("veo_usage", {}) if _state is not None else {}
    if u.get("date") != _today():
        u.clear()
        u.update(date=_today(), count=0)
    return u


def left() -> int:
    return CFG["video"].get("daily_limit", 10) - _usage()["count"]


def need(n: int):
    if left() < n:
        raise QuotaExceeded(f"needs {n} Veo videos, only {left()} left today")


def used(n: int = 1):
    _usage()["count"] += n


def exhausted():
    """Google said we're out: trust it for the rest of the Pacific day."""
    _usage()["count"] = CFG["video"].get("daily_limit", 10)


def next_reset() -> datetime:
    now = datetime.now(PT)
    reset = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
    return reset.astimezone(TZ)
