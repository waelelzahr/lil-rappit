"""Generation helpers: captions (Gemini), images (Nano Banana), video (Veo)."""
import json
import os
import subprocess
import time
from pathlib import Path

from google import genai
from google.genai import types

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


def text_json(prompt: str) -> dict:
    last_err = None
    for model in [CFG["models"]["text"], *CFG["models"].get("text_fallbacks", [])]:
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


def image(prompt: str, out: Path, extra_images: list[Path] | None = None) -> Path:
    """Generate a 9:16 image of Lil Rappit, guided by the reference images."""
    parts = _ref_parts()
    for p in extra_images or []:
        parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime_of(p)))
    parts.append(
        "The reference images show the character Lil Rappit. Keep his look exactly "
        f"the same. {LOOK}\n\nScene: {prompt}\n\n{STYLE}"
    )
    last_err = None
    for model in (CFG["models"]["image"], CFG["models"]["image_fallback"]):
        try:
            resp = client().models.generate_content(
                model=model,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="9:16"),
                ),
            )
            for part in resp.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    out.write_bytes(part.inline_data.data)
                    log(f"image ok ({model}) -> {out.name}")
                    return out
            last_err = RuntimeError(f"{model} returned no image")
        except Exception as e:  # try fallback model
            last_err = e
            log(f"image model {model} failed: {e}")
    raise last_err


def video(prompt: str, start_frame: Path, out: Path) -> Path:
    """Image-to-video with Veo, starting from start_frame."""
    v = CFG["video"]
    op = client().models.generate_videos(
        model=CFG["models"]["video"],
        prompt=f"{LOOK}\n\n{prompt}\n\n{STYLE}",
        image=types.Image(image_bytes=start_frame.read_bytes(), mime_type=mime_of(start_frame)),
        config=types.GenerateVideosConfig(
            aspect_ratio=v["aspect_ratio"],
            resolution=v["resolution"],
            duration_seconds=v["clip_seconds"],
            number_of_videos=1,
        ),
    )
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
    log(f"video ok -> {out.name} ({time.time() - t0:.0f}s)")
    return out


def last_frame(video_path: Path, out: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-sseof", "-0.1", "-i", str(video_path),
         "-frames:v", "1", "-update", "1", str(out)],
        check=True,
    )
    return out


def stitch(a: Path, b: Path, out: Path) -> Path:
    a, b = _ensure_audio(a), _ensure_audio(b)
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(a), "-i", str(b),
         "-filter_complex",
         "[0:v]scale=1080:1920,setsar=1,fps=24[v0];[1:v]scale=1080:1920,setsar=1,fps=24[v1];"
         "[0:a]aresample=48000[a0];[1:a]aresample=48000[a1];"
         "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", str(out)],
        check=True,
    )
    return out
