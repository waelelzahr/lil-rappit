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
Style: Label,{FONT},50,&H00000000,&H00000000,&H0000D7FF,&H0000D7FF,1,0,0,0,100,100,2,0,3,12,0,8,90,90,140,1

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


def speech_windows(video: Path) -> list[tuple[float, float]]:
    """When someone is speaking (any language), via multilingual Whisper segments."""
    import numpy as np
    from faster_whisper import WhisperModel
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(video), "-f", "s16le",
                          "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, vad_filter=True, language="ar")
    return [(seg.start, seg.end) for seg in segments if seg.end - seg.start > 0.2]


def apply_dialogue(video: Path, out: Path, dialogue: list[dict]) -> Path:
    """Burn the scripted lines (Lebanese in Latin letters + small English) timed to the speech."""
    lines = [d for d in dialogue if (d.get("arabizi") or d.get("english"))]
    if not lines:
        return video
    try:
        win = speech_windows(video)
    except Exception as e:
        log(f"speech timing failed: {e}")
        win = []
    if not win:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout or 10)
        win = [(0.5, dur - 0.5)]
    start, end = win[0][0], win[-1][1]
    if len(win) >= len(lines):  # one line per speech window, in order (extra windows merge)
        per = len(win) / len(lines)
        spans = [(win[int(i * per)][0], win[min(len(win) - 1, int((i + 1) * per) - 1)][1])
                 for i in range(len(lines))]
    else:  # fewer windows than lines: split the speaking time by line length
        total = sum(len(d.get("arabizi", "")) or 1 for d in lines)
        spans, t = [], start
        for d in lines:
            dur = (end - start) * (len(d.get("arabizi", "")) or 1) / total
            spans.append((t, t + dur))
            t += dur
    events = []
    for d, (a, b) in zip(lines, spans):
        text = _wrap(_esc(d.get("arabizi", "")), 22)
        if d.get("english"):
            text += f"\\N{{\\fs46\\c&HDDDDDD&}}{_wrap(_esc(d['english']), 30)}"
        events.append(f"Dialogue: 0,{_t(a)},{_t(max(b, a + 1.2))},Cap,,0,0,0,,{text}")
    ass = out.with_suffix(".ass")
    ass.write_text(ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf",
                    f"ass={ass}:fontsdir={FONT_DIR}", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    log(f"dialogue captions: {len(lines)} lines over {len(win)} speech windows")
    return out


def transcribe(video: Path, hint: str) -> list[dict]:
    """Word timestamps via faster-whisper (CPU). Returns [{start, end, word}]."""
    import numpy as np
    from faster_whisper import WhisperModel
    # Decode audio with ffmpeg ourselves (avoids PyAV version issues).
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(video), "-f", "s16le",
                          "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, word_timestamps=True, vad_filter=True,
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


def apply(video: Path, out: Path, hook: str | None, script_lines: list[str],
          sub: str | None = None, label: str | None = None) -> Path:
    """hook: big text for the first seconds; sub: smaller yellow line under it (e.g. WAIT FOR
    HIS FACE); label: small yellow tag above it (e.g. DAY 5)."""
    events = []
    if hook:
        text = _wrap(_esc(hook).upper())
        if sub:
            text += f"\\N{{\\fs60\\c&H00D7FF&}}{_esc(sub).upper()}"
        events.append(f"Dialogue: 1,{_t(0)},{_t(HOOK_SECONDS)},Hook,,0,0,0,,"
                      f"{{\\fad(120,300)}}{text}")
    if label:
        events.append(f"Dialogue: 2,{_t(0)},{_t(HOOK_SECONDS)},Label,,0,0,0,,"
                      f"{{\\fad(120,300)}}{_esc(label).upper()}")
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
