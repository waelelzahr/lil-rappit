"""Hourly job: read email replies. OK approves an item for its posting slot;
REDO (or any other reply text, used as a note) regenerates it."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rappit import items, mailer  # noqa: E402
from rappit.common import CFG, EPISODES, OUT, load_state, log, save_state  # noqa: E402

EP_BY_ID = {e["id"]: e for e in EPISODES}


def redo(state: dict, item_id: str, note: str | None):
    it = state["items"][item_id]
    if it["status"] in ("approved", "posted"):
        mailer.send_text(f"{item_id} is already {it['status']}, so I left it as is.")
        return
    if it["redos"] >= CFG["limits"]["max_redos_per_item"]:
        mailer.send_text(f"Redo limit reached for {item_id}. Reply OK to the latest "
                         "version, or raise max_redos_per_item in config.yaml.")
        return
    it["redos"] += 1
    version = it["redos"] + 1
    built = items.build(f"{item_id}-v{version}", it["kind"], EP_BY_ID[it["episode"]],
                        note=note, soft_idx=it.get("soft_idx", 0) + it["redos"])
    path = Path(built["file"])
    mailer.send_item(item_id, it["kind"], path,
                     (f"Your note: {note}\n\n" if note else "") + built["caption"],
                     title=EP_BY_ID[it["episode"]]["title"], version=version)
    it.update(run_id=os.environ.get("GITHUB_RUN_ID"), relpath=str(path.relative_to(OUT)),
              caption=built["caption"], title=built["title"], status="pending")


def main():
    state = load_state()
    seen = set(state.setdefault("seen_replies", []))
    for r in mailer.fetch_replies(seen):
        state["seen_replies"].append(r["msgid"])
        save_state(state)  # never process the same reply twice
        item_id = r["item_id"]
        if item_id not in state["items"]:
            continue
        try:
            if r["action"] == "approve":
                it = state["items"][item_id]
                if it["status"] == "pending":
                    it["status"] = "approved"
                    log(f"approved {item_id}")
            else:
                log(f"redo {item_id}: {r['note']}")
                redo(state, item_id, r["note"])
        except Exception as e:
            log(f"reply for {item_id} failed: {e}")
            mailer.send_text(f"Something failed while handling your reply for {item_id}:\n{e}",
                             subject="[Rappit] ⚠️ Problem")
        save_state(state)
    state["seen_replies"] = state["seen_replies"][-300:]
    save_state(state)


if __name__ == "__main__":
    main()
