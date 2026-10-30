"""New format: one ~10 s clip per post. Lil Rappit (tough, deadpan gangster rabbit) and his
sidekick Abu Lakma in Lebanese / Arab everyday life, music- and visual-driven comedy.
The writer invents a fresh concept each time (same fields as concepts.yaml)."""
import re

from . import gen
from .common import ROOT, log

ABU_LAKMA = ("Abu Lakma, an original huge tough boxer bulldog: broad muscular chest, short "
             "brindle fur, flat nose, small scar over one eyebrow, red velvet tracksuit, thick "
             "gold chain, white sneakers")
ABU_REF = ROOT / "state" / "refs" / "abu_lakma.png"
STYLE = ("Cinematic photoreal 3D, natural motivated lighting that fits the setting, shallow "
         "depth of field, vertical 9:16, characters fully in frame. Family-safe comedy. No "
         "subtitles, no captions, no watermarks, no smoking, no weapons.")

RULES = f"""
You invent ONE short comedy clip (exactly 10 seconds, one continuous shot) for Instagram Reels
and YouTube Shorts, for a Lebanese / Arab audience (and anyone who enjoys it).

Star: Lil Rappit, a tough gangster rabbit (black bucket hat, gold sunglasses, orange puffer
jacket, gold chain with a carrot pendant). He is always dead serious and intimidating, and that
deadpan toughness is what makes everyday situations funny. His sidekick Abu Lakma: {ABU_LAKMA}.
Use Abu Lakma in most clips (set "with_abu": true), not necessarily all.

What works (our best test was Rappit and Abu Lakma leading a dabke line at a village wedding with
mijwiz music, Rappit doing extreme dabke squats, until a grandma waves a carrot and he abandons
the dance while Abu Lakma stares into the camera):
- A situation every Lebanese person instantly recognises: family, food, weddings, traffic,
  electricity cuts, the generator guy, service taxis, Teta, the neighbourhood, the mountains,
  the souk, Sunday lunch, coffee, tawleh, summer, snow in the mountains, celebrations.
- Rappit takes it to a tough-guy EXTREME (the most intense dabke, the most serious tawleh game,
  negotiating like a mafia boss with the vegetable seller), played completely straight.
- Visual and music driven so it works without understanding words. Dialogue is optional and
  tiny: at most one or two short lines or exclamations (Lebanese Arabic in Latin letters such as
  "yalla", "khalas", "ya habibi", "ya ayb el shoum" are great), or none at all.
- A clear twist / punchline in the last 3 seconds that is VISIBLE: something unexpected
  happens, and someone (often Abu Lakma) reacts or stares into the camera in disbelief.
- Carrots are his weakness and can be the twist, but use that in at most 1 of 3 clips.
- Every prop must be visible in a character's hands or in the scene before it is used; nothing
  appears out of nowhere. Keep actions simple and physical: one location, max 3-4 characters.
- Family-friendly, no smoking or argileh, no weapons, no alcohol, no religion or politics, no
  real people or celebrities, no real songs (describe the style of music instead).
- Never use words like violent, slap, smash, attack, threatening or blood.
"""

FORMAT = """
Return JSON:
{
 "id": "short-kebab-case-id",
 "title": "2-4 word title",
 "with_abu": true or false,
 "look": "visual description of any OTHER characters (animal characters, clothes, colors), or empty string",
 "setting": "one vivid Lebanese location, time of day, lighting, background details",
 "frame": "the opening still: framing, who stands where, what each holds (every prop that will be used must already be visible)",
 "action": "[0-4s] ... [4-7s] ... [7-10s] ... beat by beat, concrete physical actions, camera moves",
 "sound": "music style (instruments), ambience, effects, and any dialogue as Speaker: \\"line\\"",
 "caption_brief": "one sentence describing the clip and its joke, for the caption writer",
 "uses_carrot": true or false
}"""


def write(done_titles: list[str], hint: str | None = None, note: str | None = None) -> dict:
    prompt = (RULES
              + (f"\nAlready made (do something different): {', '.join(done_titles[-30:])}\n"
                 if done_titles else "")
              + (f"\nBuild the clip around this idea: {hint}\n" if hint else "")
              + (f"\nDirector's note (must follow): {note}\n" if note else "")
              + FORMAT)
    c = gen.text_json(prompt, prefer_pro=True)
    c["id"] = "concept-" + re.sub(r"[^a-z0-9-]", "", str(c.get("id", "clip")).lower())[:30]
    c["concept"] = True
    c["seconds"] = 10
    c["style"] = STYLE
    if c.get("with_abu"):
        c["look"] = (ABU_LAKMA + ". " + (c.get("look") or "")).strip()
    for k in ("demand", "bad_deal"):
        c.setdefault(k, "")
    c.setdefault("opponent", c.get("look", ""))
    log(f"concept: {c.get('title')} - {c.get('caption_brief', '')}")
    return c


def script_text(c: dict) -> str:
    return (f"📜 **{c.get('title', '')}**\n**Setting:** {c.get('setting', '')}\n"
            f"**What happens:** {c.get('action', '')}\n**Sound:** {c.get('sound', '')}")[:1900]
