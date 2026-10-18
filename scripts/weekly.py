"""Sunday job: pick an unused episode, generate the week's 3 items, send to Telegram."""
import os
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rappit import items, telegram  # noqa: E402
from rappit.common import CFG, EPISODES, OUT, TZ, load_state, log, next_slot, save_state  # noqa: E402


def main():
    state = load_state()
    unused = [e for e in EPISODES if e["id"] not in state["used_episodes"]]
    if not unused:  # bank exhausted: start over
        state["used_episodes"] = []
        unused = list(EPISODES)
    ep = random.choice(unused)
    state["used_episodes"].append(ep["id"])
    week = datetime.now(TZ).strftime("%Y-%m-%d")
    soft_idx = len(state["used_episodes"])
    log(f"episode: {ep['id']} - {ep['title']}")

    errors = []
    for kind in ("reel", "mugshot", "soft"):
        item_id = f"{week}-{kind}"
        try:
            built = items.build(item_id, kind, ep, soft_idx=soft_idx)
            path = Path(built["file"])
            msg_id = telegram.send_item(
                item_id, kind, path,
                f"[{kind.upper()} · {ep['title']} · posts {CFG['schedule'][kind]}]\n\n"
                f"{built['caption']}")
            state["items"][item_id] = {
                "kind": kind, "episode": ep["id"], "slot": next_slot(CFG["schedule"][kind]),
                "status": "pending", "message_id": msg_id, "redos": 0,
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "relpath": str(path.relative_to(OUT)),
                "caption": built["caption"], "title": built["title"], "soft_idx": soft_idx,
            }
        except Exception as e:
            log(f"FAILED {item_id}: {e}")
            errors.append(f"{kind}: {e}")
        save_state(state)

    if errors:
        telegram.send_text("⚠️ Some drafts failed this week:\n" + "\n".join(errors)
                           + "\n\nRe-run the Weekly workflow on GitHub to try again.")
        sys.exit(1)
    telegram.send_text(f"🐰 This week: “{ep['title']}”. Tap Approve or Redo on each draft. "
                       "To redo with changes, reply to a draft with your note.")


if __name__ == "__main__":
    main()
