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
    last_err = None
    models = [CFG["models"]["text"], *CFG["models"].get("text_fallbacks", [])]
    if prefer_pro:
        models = [*CFG["models"].get("text_pro", []), *models]
    for model in models:
        try:
            resp = client().models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            data = json.loads(resp.text)
            if isinstance(data, list):
                data = data[0]
            return data
        except Exception as e:
            last_err = e
            log(f"text model {model} failed: {e}")
    raise last_err


_NO_SIZE: set[str] = set()  # models that rejected image_size


def _image_config(aspect: str, model: str):
    size = CFG.get("images", {}).get("size")
    if size and model not in _NO_SIZE:
        return types.ImageConfig(aspect_ratio=aspect, image_size=size)
    return types.ImageConfig(aspect_ratio=aspect)


def image(prompt: str, out: Path, extra_images: list | None = None,
          style: str | None = None, with_rappit: bool = True, aspect: str = "9:16") -> Path:
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
    for model in (CFG["models"]["image"], CFG["models"]["image_fallback"]):
        try:
            resp = client().models.generate_content(
                model=model,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=_image_config(aspect, model),
                ),
            )
            for part in resp.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    out.write_bytes(part.inline_data.data)
                    log(f"image ok ({model}) -> {out.name}")
                    return out
            last_err = RuntimeError(f"{model} returned no image")
        except Exception as e:  # retry without size, then try fallback model
            if "size" in str(e).lower() and model not in _NO_SIZE:
                _NO_SIZE.add(model)
                log(f"{model} rejected image_size; retrying at default size")
                return image(prompt, out, extra_images, style, with_rappit, aspect)
            last_err = e
            log(f"image model {model} failed: {e}")
    raise last_err


def video(prompt: str, start_frame: Path, out: Path, seconds: int | None = None,
          style: str | None = None, rappit: bool = True) -> Path:
    """Image-to-video with Veo, starting from start_frame."""
    v = CFG["video"]
    seconds = seconds or v["clip_seconds"]
    full = (f"{LOOK}\n\n" if rappit else "") + f"{prompt}\n\n{style or STYLE}"
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
