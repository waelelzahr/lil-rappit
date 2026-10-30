"""Run the weekly trend + stats research now and post the summary to Discord."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import brief, discord  # noqa: E402
from rappit.common import ROOT, load_state, save_state  # noqa: E402


def main():
    state = load_state()
    b = brief.build(state)
    save_state(state)
    (ROOT / "state" / "brief.md").write_text(
        f"# Brief {b['date']}\n\n{b['text']}\n\n## Our stats\n\n{b['stats']}\n", encoding="utf-8")
    discord.send_text(f"🔎 **Research brief**\n{b['summary']}")


if __name__ == "__main__":
    main()
