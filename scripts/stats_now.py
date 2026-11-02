"""Write current Instagram + YouTube stats to state/stats.md (no research, no cost)."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import insights  # noqa: E402
from rappit.common import ROOT, TZ  # noqa: E402

if __name__ == "__main__":
    text = insights.summary()
    (ROOT / "state" / "stats.md").write_text(
        f"# Stats {datetime.now(TZ):%Y-%m-%d %H:%M}\n\n{text}\n", encoding="utf-8")
    print(text)
