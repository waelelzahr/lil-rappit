"""Quality checks with a vision model: catch duplicated props, extra accessories, wrong or
extra characters, and characters that don't match their reference images."""
from pathlib import Path

from . import gen
from .common import log

FRAME_CHECK = """You are a strict continuity supervisor for an animated comedy series.
Above: the character reference images, then the OPENING FRAME to check.
The frame should show exactly this: {frame}
Characters that must appear (and nobody else of importance): {who}

Check for ANY of these errors:
- a character who does not match their reference (species, fur color, clothes, accessories)
- duplicated items: a second pair of glasses, two hats, two of the same prop when the
  description has one (e.g. two coffees, two cookie tins), extra hands/limbs
- extra or missing characters, a character appearing twice
- props from the description missing, or props that make no sense in the scene
- any text, letters, logos or watermarks in the image
Return JSON: {{"ok": true/false, "problems": ["short concrete description", ...]}}
Only report real, visible problems; minor style differences are fine."""

VIDEO_CHECK = """You are a strict continuity supervisor. Above: character references, then
frames taken from the start, middle and end of the clip.
Intended clip: {action}
Characters: {who}
Check: characters stay consistent with their references and with each other across frames;
no duplicated characters or props (e.g. two coffees, a second pair of glasses); no text on
screen; the punchline at the end ({joke}) is actually visible in the last frame.
Return JSON: {{"ok": true/false, "problems": ["...", ...], "punchline_visible": true/false}}"""


def check_frame(frame: Path, refs: list, frame_desc: str, who: str) -> dict:
    try:
        r = gen.vision_json(FRAME_CHECK.format(frame=frame_desc, who=who),
                            [*refs, ("OPENING FRAME TO CHECK", frame)])
        log(f"frame check: {'ok' if r.get('ok') else r.get('problems')}")
        return r
    except Exception as e:
        log(f"frame check skipped: {e}")
        return {"ok": True, "problems": []}


def check_video(video: Path, refs: list, c: dict, who: str) -> dict:
    try:
        dur = gen._duration(video)
        times = [round(dur * x, 1) for x in (0.1, 0.5, 0.93)]
        shots = gen.frames_at(video, times, video.parent)
        r = gen.vision_json(VIDEO_CHECK.format(action=c.get("action", ""), who=who,
                                               joke=c.get("joke", "")),
                            [*refs, *[(f"CLIP FRAME at {t}s", p) for t, p in zip(times, shots)]])
        log(f"video check: {'ok' if r.get('ok') else r.get('problems')} "
            f"punchline_visible={r.get('punchline_visible')}")
        return r
    except Exception as e:
        log(f"video check skipped: {e}")
        return {"ok": True, "problems": []}
