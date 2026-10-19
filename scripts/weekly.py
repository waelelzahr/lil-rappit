"""Sunday job: build the week's plan (see config.yaml `plan`), post drafts to Discord."""
import os
import random
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rappit import discord, items  # noqa: E402
from rappit.common import CFG, EPISODES, OUT, TZ, load_state, log, next_slot, save_state  # noqa: E402


def pick_episode(state: dict, forced: str = "") -> dict:
    ep = next((e for e in EPISODES if e["id"] == forced), None)
    if not ep:
        unused = [e for e in EPISODES if e["id"] not in state["used_episodes"]]
        if not unused:  # bank exhausted: start over
            state["used_episodes"] = []
            unused = list(EPISODES)
        ep = random.choice(unused)
    if ep["id"] not in state["used_episodes"]:
        state["used_episodes"].append(ep["id"])
    return ep


def main():
    state = load_state()
    week = datetime.now(TZ).strftime("%Y-%m-%d")
    only = [k.strip() for k in os.environ.get("ONLY", "").split(",") if k.strip()]
    forced = os.environ.get("EPISODE", "").strip()
    plan = [p for p in CFG["plan"] if not only or p["id"] in only or p["kind"] in only]

    # One episode per reel; photos follow the first reel's episode.
    eps = {}
    for p in plan:
        if p["kind"] == "reel":
            eps[p["id"]] = pick_episode(state, forced if not eps else "")
    first_ep = next(iter(eps.values()), None) or pick_episode(state, forced)
    titles = ", ".join(f"“{e['title']}”" for e in eps.values()) or f"“{first_ep['title']}”"
    log(f"episodes: {titles}")
    discord.send_text(f"🐰 **New week: {titles}**\nDrafts incoming…")

    errors = []
    soft_idx = len(state["used_episodes"])
    for p in plan:
        item_id = f"{week}-{p['id']}"
        ep = eps.get(p["id"], first_ep)
        try:
            built = items.build(item_id, p["kind"], ep, soft_idx=soft_idx)
            path = Path(built["file"])
            msg_id = discord.send_item(item_id, p["kind"], path,
                                       f"Posts: {p['at']}\n\n{built['caption']}", title=ep["title"])
            state["items"][item_id] = {
                "kind": p["kind"], "episode": ep["id"], "slot": next_slot(p["at"]),
                "status": "pending", "redos": 0, "message_id": msg_id,
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "relpath": str(path.relative_to(OUT)),
                "caption": built["caption"], "title": built["title"], "soft_idx": soft_idx,
            }
        except Exception as e:
            log(f"FAILED {item_id}: {e}\n{traceback.format_exc()}")
            errors.append(f"{p['id']}: {str(e)[:300]}")
        save_state(state)

    if errors:
        discord.send_text("⚠️ Some drafts failed:\n" + "\n".join(errors)
                          + "\nRe-run the *Weekly drafts* workflow on GitHub to try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
