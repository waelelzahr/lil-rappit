"""Generation helpers: captions (Gemini), images (Nano Banana), video (Veo)."""
import json
import os
import subprocess
import time
from pathlib import Path

from google import genai
from google.genai import types

from . import quota
from .common import CFG, ROOT, log

_client = None


def client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


CHARACTER = (ROOT / "character.md").read_text(encoding="utf-8")
REF_FILES = ["turnaround.jpg", "portrait.jpg", "boss_chair.jpg"]

LOOK = (
    "Lil Rappit: a realistic, plush, light-grey furry rabbit with a white fluffy "
    "chest, stocky short body, tall ears with pink inner ear (left ear tip slightly "
    "torn), black bucket hat, small gold-rimmed dark sunglasses, bright orange "
    "puffer jacket worn open with no shirt, thick gold Cuban chain with a small gold "
    "carrot pendant, one gold front tooth, black baggy pants, white sneakers."
)
STYLE = (
    "Cinematic photoreal 3D, shallow depth of field, warm film lighting, vertical "
    "9:16 composition, the character centered and fully in frame. Family-safe "
    "comedy. No subtitles, no captions, no watermarks, no smoking."
)
FILM_STILL = (
    "A single frame from a high-budget crime film, shot on 35mm anamorphic: dramatic "
    "low-key lighting with one hard motivated key light, deep black shadows, rim light "
    "separating the subject from the background, atmospheric haze catching the light, "
    "rich warm amber and teal tones, shallow depth of field with creamy bokeh, subtle film "
    "grain, deliberate composition with strong negative space. "
)
NOIR = (
    "Dark cinematic crime-drama look, like a classic mafia film: low-key chiaroscuro "
    "lighting, deep shadows, warm amber practical lamps, haze in the air, anamorphic "
    "lens, very shallow depth of field, subtle film grain, punchy motivated camera moves, "
    "vertical 9:16. Photoreal 3D characters. Family-safe. No subtitles, no captions, "
    "no watermarks, no smoking, no weapons."
)


def mime_of(path: Path) -> str:
    head = path.read_bytes()[:4]
    return "image/png" if head.startswith(b"\x89PNG") else "image/jpeg"


def _has_audio(path: Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def _ensure_audio(path: Path) -> Path:
    if _has_audio(path):
        return path
    fixed = path.with_name(path.stem + "_a.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-f", "lavfi",
                    "-i", "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "copy",
                    "-c:a", "aac", str(fixed)], check=True)
    return fixed


def _ref_parts():
    return [
        types.Part.from_bytes(data=(ROOT / "refs" / f).read_bytes(), mime_type="image/jpeg")
        for f in REF_FILES
    ]


def text_json(prompt: str, prefer_pro: bool = False) -> dict:
    from . import models

    def run(model):
        resp = client().models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"))
        data = json.loads(resp.text)
        return data[0] if isinstance(data, list) else data
    return models.call("pro" if prefer_pro else "flash", run)


def vision_json(prompt: str, images: list) -> dict:
    """Ask a text model about images. images: list of (label, Path). Returns parsed JSON."""
    parts = []
    for label, path in images:
        parts.append(f"{label}:")
        parts.append(types.Part.from_bytes(data=Path(path).read_bytes(), mime_type=mime_of(Path(path))))
    parts.append(prompt)
    from . import models

    def run(model):
        resp = client().models.generate_content(
            model=model, contents=parts,
            config=types.GenerateContentConfig(response_mime_type="application/json"))
        data = json.loads(resp.text)
        return data[0] if isinstance(data, list) else data
    return models.call("pro", run)


def frames_at(video: Path, seconds: list[float], out_dir: Path) -> list[Path]:
    out = []
    for t in seconds:
        f = out_dir / f"{video.stem}_t{t:g}.jpg"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=540:-1", str(f)], check=True)
        out.append(f)
    return out


def research(prompt: str) -> str:
    """Answer with live Google Search grounding (for weekly trend research). Plain text."""
    from . import models

    def run(model):
        resp = client().models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
        if not resp.text:
            raise RuntimeError("research returned nothing")
        return resp.text
    return models.call("pro", run)


_NO_SIZE: set[str] = set()  # models that rejected image_size


def _image_config(aspect: str, model: str):
    size = CFG.get("images", {}).get("size")
    if size and model not in _NO_SIZE:
        return types.ImageConfig(aspect_ratio=aspect, image_size=size)
    return types.ImageConfig(aspect_ratio=aspect)


_SOFTEN = {"violently": "suddenly", "violent": "sudden", "slaps": "plops", "slap": "plop",
           "smash": "drop", "smashes": "drops", "attack": "move", "kill": "end", "punch": "push",
           "threatening": "serious", "blood": "red", "aggressively": "firmly",
           "aggressive": "stern", "threatens": "warns", "threaten": "warn", "threat": "warning",
           "glaring": "staring", "glares": "stares", "snatches": "grabs", "snatch": "grab",
           "shoves": "pops", "shove": "pop", "fight": "argument", "fighting": "arguing",
           "punches": "pushes", "kills": "ends", "dies": "faints", "dead": "totally",
           "prayer beads": "worry beads", "masbaha": "worry beads"}


def soften(text: str) -> str:
    """Swap words that make the image/video models refuse a harmless comedy prompt."""
    import re
    for bad, good in _SOFTEN.items():
        text = re.sub(rf"\b{bad}\b", good, text, flags=re.I)
    return text


def image(prompt: str, out: Path, extra_images: list | None = None,
          style: str | None = None, with_rappit: bool = True, aspect: str = "9:16",
          _softened: bool = False) -> Path:
    """Generate a 9:16 image. extra_images: list of Path or (label, Path) tuples."""
    parts = []
    if with_rappit:
        parts.append("REFERENCE - Lil Rappit (keep his look exactly):")
        parts += _ref_parts()
    for item in extra_images or []:
        label, p = item if isinstance(item, tuple) else ("Additional reference", item)
        parts.append(f"REFERENCE - {label}:")
        parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime_of(p)))
    parts.append(
        (f"Lil Rappit: {LOOK}\n\n" if with_rappit else "")
        + f"Create this image. {prompt}\n\n{(style or STYLE).replace('9:16', aspect)}"
    )
    last_err = None
    from . import models as _m
    queue, tried = _m.candidates("image")[:5], set()
    while queue:
        model = queue.pop(0)
        if model in tried:
            continue
        tried.add(model)
        try:
            resp = client().models.generate_content(
                model=model,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=_image_config(aspect, model),
                ),
            )
            cand = (resp.candidates or [None])[0]
            for part in ((cand.content.parts if cand and cand.content else None) or []):
                if part.inline_data and part.inline_data.data:
                    out.write_bytes(part.inline_data.data)
                    log(f"image ok ({model}) -> {out.name}")
                    return out
            why = getattr(cand, "finish_reason", None) or getattr(resp, "prompt_feedback", None)
            last_err = RuntimeError(f"{model} returned no image ({why})")
            log(str(last_err))
            if not _softened:  # usually a wording refusal: retry once with softer words
                log("retrying with softened wording")
                return image(soften(prompt), out, extra_images, style, with_rappit, aspect, _softened=True)
        except Exception as e:  # retry without size, then try fallback model
            if "size" in str(e).lower() and model not in _NO_SIZE:
                _NO_SIZE.add(model)
                log(f"{model} rejected image_size; retrying at default size")
                return image(prompt, out, extra_images, style, with_rappit, aspect, _softened)
            last_err = e
            log(f"image model {model} failed: {e}")
            hint = _m.SUGGEST.search(str(e))
            if hint:
                queue.insert(0, hint.group(1))
    raise last_err


def _duration(path: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout.strip())


def _quota_error(e: Exception):
    if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
        quota.exhausted()
        raise quota.QuotaExceeded(f"Google's daily video limit reached: {e}") from e


class ContentBlocked(RuntimeError):
    """The video model refused the prompt (safety filter). Rewrite the idea, don't retry it."""


def _omni_call(inputs: list, seconds: int, prev_id: str | None = None):
    v = CFG["video"]
    last_err = None
    for fmt in ({"duration": f"{seconds}s"}, {}):
        for delivery in ("uri", "inline"):
            try:
                kw = {"previous_interaction_id": prev_id} if prev_id else {}
                inter = client().interactions.create(
                    model=CFG["models"]["video"], input=inputs, timeout=900,
                    response_format={"type": "video", "aspect_ratio": v["aspect_ratio"],
                                     "resolution": v.get("resolution", "720p"),
                                     "delivery": delivery, **fmt}, **kw)
                quota.used()
                return inter
            except Exception as e:
                _quota_error(e)
                if "prohibited" in str(e).lower() or "blocked" in str(e).lower():
                    raise ContentBlocked(str(e)[:300]) from e
                last_err = e
                log(f"Omni rejected {fmt or 'no duration'}/{delivery}: {str(e)[:300]}")
    raise last_err


def _omni_save(inter, raw: Path) -> Path:
    import base64
    vid = getattr(inter, "output_video", None)
    if vid is None:
        raise RuntimeError(f"video model returned no video (possibly blocked): {str(inter)[:400]}")
    if getattr(vid, "data", None):
        raw.write_bytes(base64.b64decode(vid.data))
    else:
        name = "files/" + vid.uri.split("files/")[-1].split(":")[0].split("?")[0]
        for _ in range(90):
            f = client().files.get(name=name)
            state = str(getattr(f, "state", "")).upper()
            if "ACTIVE" in state:
                break
            if "FAILED" in state:
                raise RuntimeError(f"video file failed: {f}")
            time.sleep(5)
        raw.write_bytes(client().files.download(file=name))
    return raw


def _trim(raw: Path, out: Path, seconds: float) -> Path:
    if _duration(raw) > seconds + 0.3:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-t", str(seconds),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt",
                        "yuv420p", "-c:a", "aac", "-b:a", "160k", str(out)], check=True)
    else:
        raw.replace(out)
    return out


def _first_inputs(full: str, start_frame: Path, seconds: int) -> list:
    import base64
    avoid = CFG["video"].get("negative_prompt")
    text = (f"<FIRST_FRAME> {full}\n\nThe video is exactly {seconds} seconds long and starts "
            "exactly on the given first frame." + (f"\nAvoid: {avoid}." if avoid else ""))
    return [{"type": "image", "data": base64.b64encode(start_frame.read_bytes()).decode(),
             "mime_type": mime_of(start_frame)},
            {"type": "text", "text": text}]


def _video_omni(full: str, start_frame: Path, out: Path, seconds: int) -> Path:
    """Gemini Omni Flash (Interactions API): image-to-video with sound, from a first frame."""
    t0 = time.time()
    inter = _omni_call(_first_inputs(full, start_frame, seconds), seconds)
    _trim(_omni_save(inter, out.with_name(out.stem + "_raw.mp4")), out, seconds)
    log(f"video ok -> {out.name} ({seconds}s, {time.time() - t0:.0f}s)")
    return out


def video_two_part(part1: str, part2: str, start_frame: Path, out: Path, style: str | None = None,
                   seconds: int = 10) -> Path:
    """~20 s clip: generate 10 s, then extend it by 10 s (speech continues) in the same
    interaction so characters, set and voices stay consistent."""
    t0 = time.time()
    full1 = f"{LOOK}\n\n{soften(part1)}\n\n{style or STYLE}"
    inter = _omni_call(_first_inputs(full1, start_frame, seconds), seconds)
    a = _omni_save(inter, out.with_name(out.stem + "_p1.mp4"))
    full2 = (f"Continue this exact video for {seconds} more seconds: same characters, same "
             f"place, same voices, same lighting, no cut.\n{soften(part2)}")
    try:
        inter2 = _omni_call([{"type": "text", "text": full2}], seconds, prev_id=inter.id)
        b = _omni_save(inter2, out.with_name(out.stem + "_p2.mp4"))
    except ContentBlocked:
        raise
    except Exception as e:  # extension failed: keep part 1 alone rather than nothing
        log(f"extension failed, using the first 10 s only: {e}")
        return _trim(a, out, seconds)
    if _duration(b) >= _duration(a) + seconds - 1.5:  # the extension returned the full video
        _trim(b, out, 2 * seconds)
    else:  # it returned only the new part: join them
        stitch([a, b], out)
    log(f"video ok -> {out.name} ({_duration(out):.1f}s, two parts, {time.time() - t0:.0f}s)")
    return out


def video(prompt: str, start_frame: Path, out: Path, seconds: int | None = None,
          style: str | None = None, rappit: bool = True) -> Path:
    """Image-to-video starting from start_frame (Gemini Omni Flash, or Veo for older ids)."""
    v = CFG["video"]
    if CFG["models"]["video"].startswith("gemini-omni"):
        seconds = seconds or v["clip_seconds"]
        full = (f"{LOOK}\n\n" if rappit else "") + f"{soften(prompt)}\n\n{style or STYLE}"
        return _video_omni(full, start_frame, out, seconds)
    seconds = seconds or v["clip_seconds"]
    full = (f"{LOOK}\n\n" if rappit else "") + f"{soften(prompt)}\n\n{style or STYLE}"
    last_err = None
    for res in dict.fromkeys([v["resolution"], "720p"]):  # some lengths only allow 720p
        try:
            op = client().models.generate_videos(
                model=CFG["models"]["video"],
                prompt=full,
                image=types.Image(image_bytes=start_frame.read_bytes(),
                                  mime_type=mime_of(start_frame)),
                config=types.GenerateVideosConfig(
                    aspect_ratio=v["aspect_ratio"], resolution=res,
                    duration_seconds=seconds, number_of_videos=1,
                    negative_prompt=v.get("negative_prompt") or None,
                ),
            )
            break
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                quota.exhausted()
                raise quota.QuotaExceeded(f"Google's daily Veo limit reached: {e}") from e
            last_err = e
            log(f"Veo rejected {res}/{seconds}s: {e}")
    else:
        raise last_err
    quota.used()
    t0 = time.time()
    while not op.done:
        if time.time() - t0 > 900:
            raise TimeoutError("Veo took longer than 15 minutes")
        time.sleep(10)
        op = client().operations.get(op)
    if op.error:
        raise RuntimeError(f"Veo error: {op.error}")
    vids = (op.response.generated_videos or []) if op.response else []
    if not vids:
        raise RuntimeError("Veo returned no video (possibly blocked by safety filters)")
    client().files.download(file=vids[0].video)
    vids[0].video.save(str(out))
    log(f"video ok -> {out.name} ({seconds}s, {time.time() - t0:.0f}s)")
    return out


def last_frame(video_path: Path, out: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-sseof", "-0.1", "-i", str(video_path),
         "-frames:v", "1", "-update", "1", str(out)],
        check=True,
    )
    return out


def cut(clip: Path, start: float, length: float, out: Path) -> Path:
    """A short piece of a clip (re-encoded so it joins cleanly)."""
    clip = _ensure_audio(clip)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start}", "-t", f"{length}",
                    "-i", str(clip), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", str(out)], check=True)
    return out


def stitch(clips, out: Path, b: Path | None = None) -> Path:
    """Concatenate clips (list of paths) into one 1080x1920 video."""
    if b is not None:  # old signature stitch(a, b, out)
        clips, out = [clips, out], b
    clips = [_ensure_audio(c) for c in clips]
    inputs, chains, labels = [], [], ""
    for i, c in enumerate(clips):
        inputs += ["-i", str(c)]
        chains.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                      f"crop=1080:1920,setsar=1,fps=24[v{i}];[{i}:a]aresample=48000[a{i}]")
        labels += f"[v{i}][a{i}]"
    fc = ";".join(chains) + f";{labels}concat=n={len(clips)}:v=1:a=1[v][a]"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", str(out)],
        check=True,
    )
    return out
