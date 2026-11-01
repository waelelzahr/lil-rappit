"""Sunday job: build the week's plan (see config.yaml `plan`), post drafts to Discord."""
import os
import random
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rappit import brief, concepts, discord, gen, media, pipeline, quota  # noqa: E402
from rappit.common import CFG, ROOT, TZ, all_episodes, load_state, log, next_slot, save_state  # noqa: E402


def pick_episode(state: dict, forced: str = "") -> dict:
    """Forced id > viewer ideas > unused relatable episodes > any unused episode."""
    eps = all_episodes(state)
    ep = next((e for e in eps if e["id"] == forced), None)
    if not ep and state.get("idea_queue"):
        ep = next((e for e in eps if e["id"] == state["idea_queue"].pop(0)), None)
    if not ep:
        eps = [e for e in eps if not e.get("concept")]
        unused = [e for e in eps if e["id"] not in state["used_episodes"]]
        if not unused:  # bank exhausted: start over
            state["used_episodes"] = []
            unused = list(eps)
        ep = random.choice([e for e in unused if e.get("relatable")] or unused)
    if ep["id"] not in state["used_episodes"]:
        state["used_episodes"].append(ep["id"])
    return ep


def seed_abu(state: dict):
    """Keep Abu Lakma looking like he did in the dabke test (copy that portrait once)."""
    if concepts.ABU_REF.exists():
        return
    for k, it in state["items"].items():
        if k.startswith("concept-dabke") and it.get("run_id") and it.get("relpath"):
            try:
                src = media.fetch(it["run_id"], f"{k}/character.png")
                concepts.ABU_REF.parent.mkdir(parents=True, exist_ok=True)
                concepts.ABU_REF.write_bytes(src.read_bytes())
                log("Abu Lakma reference saved from the dabke test")
                return
            except Exception as e:
                log(f"could not reuse dabke Abu Lakma: {e}")


def main():
    state = load_state()
    quota.bind(state)
    week = datetime.now(TZ).strftime("%Y-%m-%d")
    only = [k.strip() for k in os.environ.get("ONLY", "").split(",") if k.strip()]
    forced = os.environ.get("EPISODE", "").strip()
    plan = [p for p in CFG["plan"] if not only or p["id"] in only]
    prefix = os.environ.get("ITEM_PREFIX", "")
    if not only and not prefix and any(k.startswith(week) for k in state["items"]):
        log(f"drafts for {week} already exist; not making them twice")
        return

    # Mafia-format reels (old format) pick from the episode bank; concept clips are written fresh.
    eps = {}
    for p in plan:
        if p["kind"] == "reel":
            eps[p["id"]] = pick_episode(state, forced if not eps else "")
    first_ep = next(iter(eps.values()), None)
    if first_ep is None and any(p["kind"] in ("mugshot", "soft") for p in plan):
        first_ep = pick_episode(state, forced)
    seed_abu(state)
    n_concepts = sum(p["kind"] == "concept" for p in plan)
    if n_concepts:
        b = brief.build(state)
        (ROOT / "state" / "brief.md").write_text(
            f"# Brief {b['date']}\n\n{b['text']}\n\n## Our stats\n\n{b['stats']}\n", encoding="utf-8")
        save_state(state)
        discord.send_text(f"🔎 **This week's research**\n{b['summary']}")
    titles = ", ".join(f"“{e['title']}”" for e in eps.values())
    log(f"week {week}: {n_concepts} clips {titles}")
    discord.send_text(f"🐰 **New week:** {n_concepts} new clips coming" + (f", plus {titles}" if titles else "") + "…")

    errors = []
    soft_idx = len(state["used_episodes"])
    reel_plan = [p for p in plan if p["kind"] == "reel"]
    for p in plan:
        item_id = f"{os.environ.get('ITEM_PREFIX', '')}{week}-{p['id']}"
        ep = eps.get(p["id"], first_ep)
        slot = next_slot(p["at"])
        kind = p["kind"]
        tease = ""
        if kind == "concept":
            try:
                ideas = state.setdefault("concept_ideas", [])
                ep = concepts.write(state, hint=ideas.pop(0) if ideas else None)
                ep["id"] += f"-{week}"
                state.setdefault("custom_episodes", []).append(ep)
                concepts.remember(state, ep, slot[:10])
                later = [q for q in plan[plan.index(p) + 1:] if q["kind"] == "concept"]
                if ep.get("cliffhanger") and later:
                    tease = f"Part 2 {later[0]['at'].split()[0]}: {ep['cliffhanger']} 👀 Follow so you don't miss it."
                else:
                    tease = "New clip every Mon, Wed, Fri & Sat 🐰 Follow for more."
            except Exception as e:
                log(f"FAILED writing {item_id}: {e}\n{traceback.format_exc()}")
                errors.append(f"{p['id']}: {str(e)[:300]}")
                continue
            kind = "reel"
        if p["kind"] == "reel":  # give people a reason to follow
            later = reel_plan[reel_plan.index(p) + 1:]
            if later:
                day = later[0]["at"].split()[0]
                tease = f"Next episode {day}: “{eps[later[0]['id']]['title']}” 🥕 Follow so you don't miss it."
            else:
                tease = "New episode every Monday & Thursday 🥕"
        try:
            if kind == "reel" and ep.get("concept") and not p.get("make"):
                try:
                    pipeline.make(state, item_id, kind, ep, slot, soft_idx, p["at"], tease)
                except gen.ContentBlocked as e:  # rewrite the idea once, safer
                    log(f"blocked by the video filter, rewriting: {e}")
                    state["custom_episodes"].remove(ep)
                    ep = concepts.write(state, note="The previous idea was blocked by the video "
                                        f"model's safety filter ({ep.get('title')}: {ep.get('joke')}). "
                                        "Write a completely different, clearly harmless idea.")
                    ep["id"] += f"-{week}-b"
                    state["custom_episodes"].append(ep)
                    concepts.remember(state, ep, slot[:10])
                    pipeline.make(state, item_id, kind, ep, slot, soft_idx, p["at"], tease)
            elif p.get("make") and not only:  # made later in the week (Veo daily limit)
                pipeline.queue(state, item_id, kind, ep, slot, soft_idx,
                               datetime.fromisoformat(next_slot(p["make"])), "scheduled", tease)
                discord.send_text(f"🗓️ **{ep['title']}** ({p['id']}) will be made {p['make']}.")
            else:
                pipeline.make(state, item_id, kind, ep, slot, soft_idx, p["at"], tease)
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
