"""Builds the three weekly items: reel, mugshot photo, soft-side photo."""
from pathlib import Path

from . import gen
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


def caption_for(kind: str, ep: dict, note: str | None) -> dict:
    tags = CFG["hashtags"]
    what = {
        "reel": f"a 16-second comedy reel: {ep['tough']} THEN {ep['carrot']}",
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

    if kind == "reel":
        f1 = gen.image(
            f"Setting: {ep['setting']}. Opening shot, Lil Rappit looking tough and "
            f"in control. {ep['tough'].split(':')[0]}" + n, d / "frame1.png")
        c1 = gen.video(
            f"Setting: {ep['setting']}. {ep['tough']} Lil Rappit speaks in a deep, slow, "
            "gravelly gangster voice. Comedic, cinematic." + n, f1, d / "clip1.mp4")
        f2 = gen.last_frame(c1, d / "frame2.png")
        c2 = gen.video(
            f"Continue directly from this frame, same scene and lighting. {ep['carrot']} "
            "When he sees the carrots his ears droop and his voice turns high, sweet and "
            "squeaky. Hold a short silent beat before he melts. Comedic timing." + n,
            f2, d / "clip2.mp4")
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

    cap = caption_for(kind, ep, note)
    log(f"built {item_id} ({kind})")
    return {"file": str(media), **cap}
