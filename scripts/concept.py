"""Make one format-test clip from concepts.yaml and send it to Discord for approval.
Env: CONCEPT (id), SLOT ("Saturday 18:00" style, Beirut time)."""
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import concepts, pipeline, quota  # noqa: E402
from rappit.common import ROOT, TZ, load_state, next_slot, save_state  # noqa: E402


def main():
    state = load_state()
    quota.bind(state)
    cid = os.environ["CONCEPT"].strip()
    if cid in ("new", ""):  # let the writer invent one (optionally around HINT)
        if os.environ.get("RESEARCH", "").strip() == "yes" or not state.get("brief"):
            from rappit import brief
            brief.build(state)
            save_state(state)
        ep = concepts.write(state, hint=os.environ.get("HINT", "").strip() or None)
        concepts.remember(state, ep, datetime.now(TZ).strftime("%Y-%m-%d"))
        cid = ep["id"]
    else:
        c = next(x for x in yaml.safe_load((ROOT / "concepts.yaml").read_text(encoding="utf-8"))
                 if x["id"] == cid)
        ep = {**c, "concept": True, "demand": "", "bad_deal": "", "opponent": c.get("look", "")}
    custom = [e for e in state.setdefault("custom_episodes", []) if e["id"] != cid]
    state["custom_episodes"] = custom + [ep]  # so redo/post can find it
    from weekly import seed_abu
    seed_abu(state)
    at = os.environ.get("SLOT", "").strip() or "Saturday 18:00"
    item_id = f"{cid}-{datetime.now(TZ):%Y-%m-%d-%H%M}"
    pipeline.make(state, item_id, "reel", ep, next_slot(at), 0, at)
    save_state(state)


if __name__ == "__main__":
    main()
