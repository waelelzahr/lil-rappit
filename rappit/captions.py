"""Burned-in hook text + word-timed captions (TikTok style) for reels."""
import re
import subprocess
from pathlib import Path

from .common import log

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT = "DejaVu Sans"
HOOK_SECONDS = 3.0

ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,7,2,2,80,80,560,1
Style: Hook,{FONT},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,3,18,0,8,90,90,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _t(sec: float) -> str:
    sec = max(0.0, sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    return re.sub(r"[{}\\]", "", text).replace("\n", " ").strip()


def _wrap(text: str, width: int = 18) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return r"\N".join(lines)


def transcribe(video: Path, hint: str) -> list[dict]:
    """Word timestamps via faster-whisper (CPU). Returns [{start, end, word}]."""
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(video), word_timestamps=True, vad_filter=True,
                                   initial_prompt=hint[:800], language="en")
    words = []
    for seg in segments:
        for w in seg.words or []:
            txt = w.word.strip()
            if txt:
                words.append({"start": w.start, "end": w.end, "word": txt})
    return words


def chunk(words: list[dict], max_words: int = 3, max_gap: float = 0.6) -> list[dict]:
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > max_gap
                    or cur[-1]["word"].endswith((".", "?", "!", ","))):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return [{"start": c[0]["start"], "end": max(c[-1]["end"], c[0]["start"] + 0.35),
             "text": " ".join(x["word"] for x in c)} for c in out]


def apply(video: Path, out: Path, hook: str | None, script_lines: list[str]) -> Path:
    events = []
    if hook:
        events.append(f"Dialogue: 1,{_t(0)},{_t(HOOK_SECONDS)},Hook,,0,0,0,,"
                      f"{{\\fad(120,300)}}{_wrap(_esc(hook).upper())}")
    try:
        words = transcribe(video, " ".join(script_lines))
        for c in chunk(words):
            events.append(f"Dialogue: 0,{_t(c['start'])},{_t(c['end'])},Cap,,0,0,0,,"
                          f"{_esc(c['text']).upper()}")
        log(f"captions: {len(words)} words")
    except Exception as e:  # captions are a bonus; never block the reel
        log(f"captions skipped: {e}")
    if not events:
        return video
    ass = out.with_suffix(".ass")
    ass.write_text(ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf",
                    f"ass={ass}:fontsdir={FONT_DIR}", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    return out
