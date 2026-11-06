"""Self-healing model choice. Google keeps renaming and retiring models; instead of failing,
we ask the API which models exist, rank them, and follow any 'please use models/X' hint in an
error. Whatever works is remembered for the rest of the run."""
import re

from .common import CFG, log

_available: list[str] | None = None
_working: dict[str, str] = {}
SUGGEST = re.compile(r"use models/([A-Za-z0-9.\-_]+)")
NOT_FOUND = ("404", "NOT_FOUND", "no longer available", "not found")


def _version(name: str) -> tuple:
    m = re.search(r"(\d+(?:\.\d+)?)", name)
    v = float(m.group(1)) if m else 0.0
    return (v, "preview" not in name and "exp" not in name)  # newest first, stable before preview


def available() -> list[str]:
    """Model names this API key can call for generateContent (cached per run)."""
    global _available
    if _available is None:
        from .gen import client
        names = []
        try:
            for m in client().models.list():
                acts = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None) or []
                if not acts or "generateContent" in acts:
                    names.append(m.name.split("/")[-1])
        except Exception as e:
            log(f"could not list models: {e}")
        _available = names
    return _available


def discovered(role: str) -> list[str]:
    bad = ("embedding", "tts", "live", "audio", "aqa", "robotics", "computer", "gemma", "learnlm")
    names = [n for n in available() if n.startswith("gemini") and not any(b in n for b in bad)]
    if role == "pro":
        names = [n for n in names if "-pro" in n and "image" not in n]
    elif role == "flash":
        names = [n for n in names if "flash" in n and "image" not in n and "lite" not in n]
    elif role == "image":
        names = [n for n in names if "image" in n or "nano-banana" in n]
    return sorted(names, key=_version, reverse=True)


def candidates(role: str) -> list[str]:
    """Ordered, de-duplicated list: what worked this run, config, then the newest discovered."""
    m = CFG["models"]
    configured = {
        "pro": [*m.get("text_pro", []), m["text"], *m.get("text_fallbacks", [])],
        "flash": [m["text"], *m.get("text_fallbacks", [])],
        "image": [m["image"], m.get("image_fallback")],
    }[role]
    extra = discovered(role) + (discovered("flash") if role == "pro" else [])
    out = []
    for n in [_working.get(role), *configured, *extra]:
        if n and n not in out:
            out.append(n)
    return out


def call(role: str, fn):
    """Run fn(model) with the best model for the role; on 'model gone' errors try the next
    one, including the replacement Google suggests in the error message."""
    tried, queue, last_err = set(), candidates(role), None
    while queue:
        model = queue.pop(0)
        if model in tried:
            continue
        tried.add(model)
        try:
            result = fn(model)
            if _working.get(role) != model:
                _working[role] = model
                log(f"using {model} for {role}")
            return result
        except Exception as e:
            last_err = e
            text = str(e)
            gone = any(k in text for k in NOT_FOUND)
            log(f"{role} model {model} failed: {text[:200]}")
            hint = SUGGEST.search(text)
            if hint and hint.group(1) not in tried:
                queue.insert(0, hint.group(1))
            if not gone and len(tried) >= 3:
                break  # a real error (not a retired model): don't burn through every model
    raise last_err


def health() -> dict:
    """Which model each role resolves to right now (cheap one-word calls)."""
    from .gen import client
    report = {}
    for role in ("pro", "flash"):
        try:
            report[role] = call(role, lambda mdl: (client().models.generate_content(
                model=mdl, contents="Reply with the single word: ok"), mdl)[1])
        except Exception as e:
            report[role] = f"FAILED: {str(e)[:120]}"
    report["image"] = (candidates("image") or ["?"])[0]
    return report
