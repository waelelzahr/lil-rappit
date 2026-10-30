"""Builds the three weekly items: reel, mugshot photo, soft-side photo."""
import json
from pathlib import Path

from . import captions, gen, quota, writer
from .common import CFG, OUT, ROOT, log

SOFT_IDEAS = (
    "secretly tending a tiny carrot garden at sunrise, watering can in paw",
    "wrapped in a fluffy blanket reading a cookbook titled CARROTS",
    "giving a carrot to a tiny baby bunny, trying to look tough but smiling",
    "at a farmers market, sunglasses on, carefully choosing the perfect carrot",
    "napping in a hammock hugging a giant plush carrot",
    "baking a carrot cake in a cozy kitchen, flour on his orange jacket",
)


def _note(note: str | None) -> str:
    return f"\nDirector's note for this version: {note}" if note else ""


def caption_for(kind: str, ep: dict, note: str | None, deal: str | None = None,
                relatable: str | None = None) -> dict:
    tags = CFG["hashtags"]
    what = {
        "reel": f"a short mafia-parody reel '{ep['title']}': Lil Rappit demands {ep['demand']}, "
                f"then gets offered carrots and accepts this: {deal or ep['bad_deal']}. "
                f"Everyday situation it parodies: {relatable or 'a negotiation gone wrong'}",
        "mugshot": f"a photo: Lil Rappit's police mugshot after the episode '{ep['title']}'",
        "soft": "a photo showing Lil Rappit's secret soft side with carrots",
    }[kind]
    data = gen.text_json(
        "You write social captions for Lil Rappit, a tough gangster rabbit whose only "
        "weakness is carrots. Write for Instagram Reels and YouTube Shorts. The goal is shares "
        "and comments from people who do not follow the account yet.\n"
        f"Post: {what}\n"
        "Return JSON with keys:\n"
        " caption: line 1 = relatable meme framing people want to send to a friend "
        "('Me when...', 'Tag the friend who...', 'POV: ...'), with plain searchable words like "
        "'funny rabbit', 'negotiation', 'salary'; 1-2 emojis. Line 2 = a short question that "
        "invites a comment answer, ideally 'What should Rappit negotiate next?' or a variant. "
        "No hashtags.\n"
        " title: YouTube Shorts title, max 70 chars, relatable and searchable, no hashtags."
        + _note(note)
    )
    return {"caption": f"{data['caption'].strip()}\n\n{tags}", "title": data["title"].strip()}


def build_concept(item_id: str, c: dict, note: str | None = None) -> dict:
    """A single ~10 s format-test clip (see concepts.yaml)."""
    d = OUT / item_id
    d.mkdir(parents=True, exist_ok=True)
    n = _note(note)
    secs = int(c.get("seconds", 10))
    quota.need(1)
    from . import concepts
    import shutil
    extra = []
    if c.get("with_abu") or c["id"] == "concept-dabke":
        if not concepts.ABU_REF.exists():  # first time: draw Abu Lakma once and keep him
            concepts.ABU_REF.parent.mkdir(parents=True, exist_ok=True)
            ref = gen.image(f"Character reference portrait of {concepts.ABU_LAKMA}. Full body and "
                            "face clearly visible, neutral pose, plain backdrop.",
                            d / "abu_lakma.png", style=c["style"], with_rappit=False)
            shutil.copy(ref, concepts.ABU_REF)
        extra.append(("Abu Lakma, the bulldog - must look exactly like this", concepts.ABU_REF))
    others = (c.get("look") or "").replace(concepts.ABU_LAKMA, "").strip(" .")
    if others:
        ref = gen.image(f"Character reference sheet of: {others}. Full body and faces clearly "
                        "visible, neutral poses, plain backdrop.", d / "character.png",
                        style=c["style"], with_rappit=False)
        extra.append(("The other characters - must look exactly like this", ref))
    frame = gen.image(f"Setting: {c['setting']}. {c['frame']}" + n, d / "frame1.png",
                      extra_images=extra, style=c["style"])
    prompt = (f"Setting: {c['setting']}.\n"
              + (f"Other character (looks exactly like this): {c['look']}.\n" if c.get("look") else "")
              + f"Action, beat by beat: {c['action']}\nSound: {c['sound']}" + n)
    media = gen.video(prompt, frame, d / "reel.mp4", seconds=secs, style=c["style"])
    try:
        data = gen.text_json(
            "You write social captions for Lil Rappit, a tough gangster rabbit whose only weakness "
            f"is carrots. Video: {c['caption_brief']}\nReturn JSON with keys: caption (line 1 = "
            "funny, shareable, 1-2 emojis; line 2 = a short question that invites comments; no "
            "hashtags), title (YouTube Shorts title, max 70 chars, no hashtags).")
        cap = {"caption": f"{data['caption'].strip()}\n\n{CFG['hashtags']}", "title": data["title"].strip()}
    except Exception as e:
        log(f"caption failed, using fallback: {e}")
        cap = {"caption": f"Lil Rappit: {c['title']} 🥕\n\n{CFG['hashtags']}", "title": f"Lil Rappit: {c['title']}"}
    log(f"built {item_id} (concept {c['id']})")
    return {"file": str(media), **cap, "script_text": concepts.script_text(c)}


def build(item_id: str, kind: str, ep: dict, note: str | None = None, soft_idx: int = 0,
          no: int | None = None) -> dict:
    if ep.get("concept"):
        return build_concept(item_id, ep, note)
    d = OUT / item_id
    d.mkdir(parents=True, exist_ok=True)
    n = _note(note)

    deal = None
    relatable = None
    if kind == "reel":
        quota.need(len(writer.SHOTS))  # never start a reel we can't finish today
        script = writer.write_script(ep, note, no)
        deal = script.get("deal")
        relatable = script.get("relatable")
        (d / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
        keep = ROOT / "state" / "scripts"  # committed with state, so scripts are readable in the repo
        keep.mkdir(parents=True, exist_ok=True)
        (keep / f"{item_id}.json").write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
        (keep / f"{item_id}.md").write_text(writer.readable(script, ep["title"]), encoding="utf-8")
        opp = gen.image(
            f"Character reference portrait of {script.get('opponent_look', ep['opponent'])}. "
            "Full body and face clearly visible, neutral pose, plain dark backdrop.",
            d / "opponent.png", style=gen.NOIR, with_rappit=False)
        OPP = ("The other character - must look exactly like this", opp)
        frames, clips = [], []
        for i, (name, secs, _) in enumerate(writer.SHOTS):
            shot = script["shots"][i]
            extra = [OPP]
            if frames:
                extra.append(("Same location, set and lighting as this earlier shot", frames[0]))
            f = gen.image(gen.FILM_STILL + f"Setting: {ep['setting']}. Shot {i + 1} ({name}): "
                          f"{shot['frame']} Camera: {shot.get('camera', '')}. "
                          f"Lighting: {shot.get('lighting', '')}." + n,
                          d / f"frame{i + 1}.png", extra_images=extra, style=gen.NOIR)
            frames.append(f)
            clips.append(gen.video(writer.shot_prompt(ep, script, i), f,
                                   d / f"shot{i + 1}.mp4", seconds=secs, style=gen.NOIR))
        rc = CFG.get("reel", {})
        if rc.get("cold_open", True):
            idx, start, length = writer.COLD_OPEN
            try:  # start the reel on his squeaky "Carrots?" so the sound itself is the hook
                words = captions.transcribe(clips[idx], "Carrots?")
                hit = next((w for w in words if writer.COLD_OPEN_WORD in w["word"].lower()), None)
                if hit:
                    start, length = max(0.0, hit["start"] - 0.15), max(1.2, hit["end"] - hit["start"] + 0.5)
                    log(f"cold open on '{hit['word']}' at {start:.2f}s for {length:.2f}s")
            except Exception as e:
                log(f"cold open word search failed, using default cut: {e}")
            try:
                cold = gen.cut(clips[idx], start, length, d / "cold_open.mp4")
                clips = [cold, *clips]
            except Exception as e:  # never lose a finished reel over the teaser
                log(f"cold open failed, skipping: {e}")
        raw = gen.stitch(clips, d / "reel_raw.mp4")
        lines = [dl.get("line", "") for sh in script["shots"] for dl in sh.get("dialogue", [])]
        media = captions.apply(
            raw, d / "reel.mp4", script.get("hook") if rc.get("hook_text", True) else None, lines,
            sub=writer.HOOK_SUB, label=f"Day {no}" if no and rc.get("day_label", True) else None)
    elif kind == "mugshot":
        media = gen.image(
            "Police booking mugshot photo: Lil Rappit stands in front of a height chart, "
            "holding a black placard that reads LIL RAPPIT, trying to look tough but "
            f"clutching a carrot. Fits the story '{ep['title']}'." + n, d / "mugshot.png", aspect="4:5")
    else:
        idea = SOFT_IDEAS[soft_idx % len(SOFT_IDEAS)]
        media = gen.image(f"Lil Rappit {idea}. Soft, warm, wholesome mood." + n,
                          d / "soft.png", aspect="4:5")

    try:
        cap = caption_for(kind, ep, note, deal, relatable)
    except Exception as e:
        log(f"caption failed, using fallback: {e}")
        cap = {"caption": f"Lil Rappit in: {ep['title']} 🥕\n\n{CFG['hashtags']}",
               "title": f"Lil Rappit: {ep['title']}"}
    log(f"built {item_id} ({kind})")
    res = {"file": str(media), **cap}
    if kind == "reel":
        res["script_text"] = writer.dialogue_only(script)
    return res
