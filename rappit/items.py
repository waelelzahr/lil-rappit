"""Builds the three weekly items: reel, mugshot photo, soft-side photo."""
from pathlib import Path

from . import gen, writer
from .common import CFG, OUT, log

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


def caption_for(kind: str, ep: dict, note: str | None, deal: str | None = None) -> dict:
    tags = CFG["hashtags"]
    what = {
        "reel": f"a 16-second comedy reel '{ep['title']}': Lil Rappit demands {ep['demand']}, "
                f"then gets offered carrots and accepts this: {deal or ep['bad_deal']}",
        "mugshot": f"a photo: Lil Rappit's police mugshot after the episode '{ep['title']}'",
        "soft": "a photo showing Lil Rappit's secret soft side with carrots",
    }[kind]
    data = gen.text_json(
        "You write social captions for Lil Rappit, a tough gangster rabbit whose only "
        "weakness is carrots. Write for Instagram Reels and YouTube Shorts.\n"
        f"Post: {what}\n"
        "Return JSON with keys: caption (max 2 short lines, punchy, 1-2 emojis, no "
        "hashtags), title (YouTube Shorts title, max 70 chars, no hashtags)."
        + _note(note)
    )
    return {"caption": f"{data['caption'].strip()}\n\n{tags}", "title": data["title"].strip()}


def build(item_id: str, kind: str, ep: dict, note: str | None = None, soft_idx: int = 0) -> dict:
    d = OUT / item_id
    d.mkdir(parents=True, exist_ok=True)
    n = _note(note)

    deal = None
    if kind == "reel":
        script = writer.write_script(ep, note)
        deal = script.get("deal")
        (d / "script.json").write_text(__import__("json").dumps(script, indent=2), encoding="utf-8")
        s1, s2 = script["shot1"], script["shot2"]
        f1 = gen.image(f"Setting: {ep['setting']}. Other character: {ep['opponent']}. "
                       f"{s1['frame']}", d / "frame1.png")
        c1 = gen.video(writer.shot_prompt(ep, s1), f1, d / "clip1.mp4")
        last = gen.last_frame(c1, d / "clip1_last.png")
        f2 = gen.image(f"Same location, lighting and other character as in the LAST reference "
                       f"image. Close-up shot. {s2['frame']}", d / "frame2.png",
                       extra_images=[last])
        c2 = gen.video(writer.shot_prompt(ep, s2, soft=True), f2, d / "clip2.mp4")
        media = gen.stitch(c1, c2, d / "reel.mp4")
    elif kind == "mugshot":
        media = gen.image(
            "Police booking mugshot photo: Lil Rappit stands in front of a height chart, "
            "holding a black placard that reads LIL RAPPIT, trying to look tough but "
            f"clutching a carrot. Fits the story '{ep['title']}'." + n, d / "mugshot.png")
    else:
        idea = SOFT_IDEAS[soft_idx % len(SOFT_IDEAS)]
        media = gen.image(f"Lil Rappit {idea}. Soft, warm, wholesome mood." + n,
                          d / "soft.png")

    try:
        cap = caption_for(kind, ep, note, deal)
    except Exception as e:
        log(f"caption failed, using fallback: {e}")
        cap = {"caption": f"Lil Rappit in: {ep['title']} 🥕\n\n{CFG['hashtags']}",
               "title": f"Lil Rappit: {ep['title']}"}
    log(f"built {item_id} ({kind})")
    return {"file": str(media), **cap}
