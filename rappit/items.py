"""Builds the three weekly items: reel, mugshot photo, soft-side photo."""
import json
from pathlib import Path

from . import captions, gen, quota, writer
from .common import CFG, OUT, ROOT, log
import re

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


class QualityFailed(RuntimeError):
    """Both video takes failed the checker; don't send a bad draft."""


def build_concept(item_id: str, c: dict, note: str | None = None) -> dict:
    """A single ~10 s format-test clip (see concepts.yaml)."""
    d = OUT / item_id
    d.mkdir(parents=True, exist_ok=True)
    n = _note(note)
    secs = int(c.get("seconds", 10))
    two_part = secs > 10 and c.get("action_1") and c.get("action_2")
    quota.need(2 if two_part else 1)
    from . import concepts
    import shutil
    extra = []
    cast = list(c.get("cast") or (["abu_lakma"] if c.get("with_abu") or c["id"] == "concept-dabke" else []))
    for key in cast:  # each recurring character is drawn once and then reused
        ref = concepts.ref_path(key)
        if not ref.exists():
            ref.parent.mkdir(parents=True, exist_ok=True)
            img = gen.image(f"Character reference portrait of {concepts.CAST[key]}. Full body and "
                            "face clearly visible, neutral pose, plain backdrop.",
                            d / f"{key}.png", style=c["style"], with_rappit=False)
            shutil.copy(img, ref)
        name = concepts.CAST[key].split(",")[0].split(":")[0]
        extra.append((f"{name} - must look exactly like this", ref))
    others = c.get("look") or ""
    for key in cast:
        others = others.replace(concepts.CAST[key], "")
    others = others.strip(" .")
    if others:
        ref = gen.image(f"Character reference sheet of: {others}. Full body and faces clearly "
                        "visible, neutral poses, plain backdrop.", d / "character.png",
                        style=c["style"], with_rappit=False)
        extra.append(("The other characters - must look exactly like this", ref))
    from . import qa
    who = ", ".join(["Lil Rappit", *[concepts.CAST[k].split(",")[0].split(":")[0] for k in cast]])
    rules = ("Exactly these characters, each appearing once: " + who + ". Every prop appears "
             "exactly once unless stated otherwise; each character wears only their own "
             "accessories (one pair of glasses at most, one hat at most). No text anywhere.")
    refs = [("Lil Rappit - must look exactly like this", ROOT / "refs" / "turnaround.jpg"), *extra]
    fix = ""
    for attempt in range(3):  # draw the opening frame, check it, redraw with the problems listed
        frame = gen.image(f"Setting: {c['setting']}. {c['frame']} {rules}" + fix + n,
                          d / f"frame1_v{attempt + 1}.png", extra_images=extra, style=c["style"])
        r = qa.check_frame(frame, refs, c["frame"], who)
        if r.get("ok"):
            break
        fix = " FIX THESE PROBLEMS FROM THE LAST ATTEMPT: " + "; ".join(r.get("problems", []))
    def speech(part=None):
        out = ""
        for dl in c.get("dialogue") or []:
            if part and int(dl.get("part") or 1) != part:
                continue
            voice = (" in a deep, slow, raspy, intimidating gangster voice"
                     if str(dl.get("speaker", "")).lower().startswith(("rappit", "lil")) else "")
            out += (f"\n{dl.get('speaker', '')} says{voice}, in Lebanese Arabic dialect, at "
                    f"{dl.get('at', '')}: \"{dl.get('arabic') or dl.get('arabizi', '')}\"")
        return (f"\nDialogue (spoken in Lebanese Arabic, lip-synced, only these lines):{out}"
                if out else "\nNo dialogue in this part.")

    head = (f"Setting: {c['setting']}.\n"
            + (f"Characters (look exactly like this): {c['look']}.\n" if c.get("look") else "")
            + f"{rules}\nSound: {c['sound']}")
    if two_part:
        p1 = f"{head}\nAction, beat by beat: {c['action_1']}{speech(1)}{n}"
        p2 = f"Action, beat by beat: {c['action_2']}{speech(2)}\nSound: {c['sound']}{n}"
        prompt = p1 + "\n" + p2
    else:
        prompt = f"{head}\nAction, beat by beat: {c['action']}{speech()}{n}"
    def score(r):  # fewest severe problems, then punchline on screen, then fewest minor ones
        return (-len(r.get("severe") or []), r.get("punchline_visible") is not False,
                -len(r.get("minor") or []))

    def make_video(extra_note: str, out):
        if two_part:
            return gen.video_two_part(p1 + extra_note, p2 + extra_note, frame, out, style=c["style"])
        return gen.video(prompt + extra_note, frame, out, seconds=secs, style=c["style"])

    media = make_video("", d / "reel.mp4")
    c["takes"] = 1
    r = qa.check_video(media, refs, c, who)
    # Only a SEVERE problem is worth paying for a second take; minor glitches go to you to judge.
    if r.get("severe"):
        quota.need(2 if two_part else 1)
        v2 = make_video("\nAVOID THESE PROBLEMS SEEN IN THE LAST ATTEMPT: " + "; ".join(r["severe"]),
                        d / "reel_v2.mp4")
        c["takes"] = 2
        r2 = qa.check_video(v2, refs, c, who)
        if score(r2) > score(r):
            media, r = v2, r2
        log(f"kept {media.name}")
    c["qa_severe"] = r.get("severe") or []
    c["qa"] = [*(r.get("severe") or []), *(r.get("minor") or [])]
    if r.get("punchline_visible") is False and not c["qa_severe"]:
        c["qa_severe"] = ["the ending/punchline may not be visible"]
    # Never throw a paid clip away: it always comes to you, with the checker's notes.
    if c.get("dialogue"):  # Lebanese lines + English, so it works with the sound off
        try:
            media = captions.apply_dialogue(media, media.with_name("reel_cap.mp4"), c["dialogue"])
        except Exception as e:
            log(f"dialogue captions failed: {e}")
    else:
        lines = re.findall(r'"([^"]{2,120})"', c.get("sound", ""))
        if lines:
            media = captions.apply(media, media.with_name("reel_cap.mp4"), None, lines)
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
    cost = round(0.1 + 1.0 * c.get("takes", 1), 2)
    if c.get("qa_severe"):
        qa_note = "\n⚠️ **Checker found serious problems:** " + "; ".join(c["qa_severe"])
    elif c.get("qa"):
        qa_note = "\n🔍 Minor checker notes: " + "; ".join(c["qa"])
    else:
        qa_note = "\n🔍 Checker: no problems found."
    qa_note += f"\n💵 Cost: about ${cost:.2f} ({c.get('takes', 1)} take{'s' if c.get('takes', 1) > 1 else ''})"
    return {"file": str(media), **cap, "script_text": concepts.script_text(c) + qa_note, "cost": cost}


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
