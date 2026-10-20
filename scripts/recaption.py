"""Re-apply hook + captions to existing reel drafts (no regeneration cost).
Usage: ITEMS=2026-10-19-reel,2026-10-19-reel2 python scripts/recaption.py"""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import captions, discord, media  # noqa: E402
from rappit.common import OUT, episode, load_state, log, save_state  # noqa: E402


def main():
    state = load_state()
    for item_id in [i.strip() for i in os.environ["ITEMS"].split(",") if i.strip()]:
        it = state["items"][item_id]
        folder = str(Path(it["relpath"]).parent)
        raw = media.fetch(it["run_id"], f"{folder}/reel_raw.mp4")
        script = json.loads(media.fetch(it["run_id"], f"{folder}/script.json").read_text())
        d = OUT / f"{folder}-cap"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(raw, d / "reel_raw.mp4")
        lines = [dl.get("line", "") for sh in script["shots"] for dl in sh.get("dialogue", [])]
        out = captions.apply(d / "reel_raw.mp4", d / "reel.mp4", script.get("hook"), lines)
        was_approved = it["status"] == "approved" or (
            it["status"] == "pending" and discord.reacted(it["message_id"], discord.APPROVE))
        it["message_id"] = discord.send_item(item_id, "reel", out, it["caption"],
                                             title=episode(state, it["episode"])["title"])
        it.update(run_id=os.environ.get("GITHUB_RUN_ID"), relpath=str(out.relative_to(OUT)))
        if was_approved:  # carry the approval over to the captioned version
            it["status"] = "approved"
            discord.send_text("✅ Your approval carries over to this captioned version.",
                              reply_to=it["message_id"])
        save_state(state)
        log(f"recaptioned {item_id}")


if __name__ == "__main__":
    main()
