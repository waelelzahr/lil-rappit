"""New format: one ~10 s clip per post. Lil Rappit (tough, deadpan gangster rabbit) and his
sidekick Abu Lakma in Lebanese / Arab everyday life, music- and visual-driven comedy.
The writer invents a fresh concept each time (same fields as concepts.yaml)."""
import re

from . import gen
from .common import ROOT, log

ABU_LAKMA = ("Abu Lakma, an original huge tough boxer bulldog: broad muscular chest, short "
             "brindle fur, flat nose, small scar over one eyebrow, red velvet tracksuit, thick "
             "gold chain, white sneakers")
ABU_REF = ROOT / "state" / "refs" / "abu_lakma.png"  # same as ref_path("abu_lakma")
LOLA = ("Lola, Rappit's glamorous girlfriend: an original white rabbit with long lashes, glossy "
        "pink lipstick, gold hoop earrings, a fluffy pink faux-fur coat and a tiny designer "
        "handbag")
TETA = ("Teta, Rappit's tiny strict grandmother: an old silver-grey rabbit with round glasses "
        "on a chain, hair in a neat bun, floral house dress, beige cardigan and slippers")
# Recurring cast (Rappit himself always uses the refs/ photos). Each keeps one reference image.
CAST = {"abu_lakma": ABU_LAKMA, "lola": LOLA, "teta": TETA}


def ref_path(key: str):
    return ROOT / "state" / "refs" / f"{key}.png"


def recent_story(state: dict, n: int = 8) -> str:
    log_ = state.get("story_log", [])[-n:]
    return "\n".join(f"- {e['date']} \"{e['title']}\": {e['summary']}"
                     + (f" (cliffhanger: {e['cliffhanger']})" if e.get("cliffhanger") else "")
                     for e in log_) or "(nothing yet)"
STYLE = ("Cinematic photoreal 3D, natural motivated lighting that fits the setting, shallow "
         "depth of field, vertical 9:16, characters fully in frame. Family-safe comedy. No "
         "subtitles, no captions, no watermarks, no smoking, no weapons.")

RULES = f"""
You are the head writer of "Lil Rappit", a comedy series of short clips (exactly 10 seconds,
one continuous shot each) for Instagram Reels and YouTube Shorts. Main audience: Lebanese and
Arab viewers, but anyone should enjoy it. Goal: views, shares and FOLLOWS (people coming back).

RECURRING CAST (use their exact names; keep them consistent):
- Lil Rappit: a tough gangster rabbit (black bucket hat, gold sunglasses, orange puffer jacket,
  gold chain with a carrot pendant). Always dead serious and intimidating; that deadpan
  toughness in silly everyday situations is the core comedy. Secret weakness: carrots.
- Abu Lakma: {ABU_LAKMA}. Rappit's loyal sidekick; the straight man who stares into the camera
  when things go wrong. In most clips.
- Lola: {LOLA}. Rappit's girlfriend: dramatic, glamorous, jealous of carrots (Rappit's one true
  love), soap-opera energy. Source of DRAMA arcs: suspicious texts, a rival, breakups and
  makeups. In about 1 of 4 clips.
- Teta: {TETA}. Rappit's grandmother; the only one he fears; she always wins. Occasionally.
New one-off characters are fine (animal characters, described in "look").

WHAT WORKS (our best clip so far: Rappit and Abu Lakma leading a dabke line at a village
wedding to mijwiz music, Rappit doing extreme dabke squats, until a grandma waves a carrot and
he abandons the dance while Abu Lakma stares into the camera):
- A situation Lebanese people instantly recognise (family, food, weddings, traffic, power cuts,
  the generator guy, service taxis, Teta, neighbours, the mountains, the souk, Sunday lunch,
  coffee, tawleh, summer, snow) or a format that is trending right now (see TREND BRIEF).
- Rappit takes it to a tough-guy EXTREME, played completely straight.
- Visual and music driven so it works without words. Dialogue optional and tiny: at most one or
  two short lines (Lebanese Arabic in Latin letters such as "yalla", "khalas", "ya habibi" is
  great), or none.
- A VISIBLE twist / punchline in the last 3 seconds and a reaction (often a stare into camera).
- Drama brings people back: sometimes continue a storyline from RECENT EPISODES (Lola arcs,
  rivalries, Teta's verdicts) and end on a cliffhanger, but most clips must also be funny on
  their own for new viewers.
- Carrots can be the twist, but in at most 1 of 3 clips.
- Every prop must be visible in a character's hands or in the scene before it is used; nothing
  appears out of nowhere. Simple physical actions, one location, max 4 characters on screen.
- Family-friendly: no smoking or argileh, no weapons, no alcohol, no religion or politics, no
  real people or celebrities, no real songs (describe the style of music instead), no romance
  beyond PG soap-opera drama.
- Never use words like violent, slap, smash, attack, threatening or blood.
"""

FORMAT = """
Return JSON:
{
 "id": "short-kebab-case-id",
 "title": "2-4 word title",
 "cast": ["abu_lakma", "lola", "teta"] (only the recurring characters who appear; can be empty),
 "look": "visual description of any NEW one-off characters (animal characters, clothes, colors), or empty string",
 "setting": "one vivid Lebanese location, time of day, lighting, background details",
 "frame": "the opening still: framing, who stands where, what each holds (every prop that will be used must already be visible)",
 "action": "[0-4s] ... [4-7s] ... [7-10s] ... beat by beat, concrete physical actions, camera moves",
 "sound": "music style (instruments), ambience, effects, and any dialogue as Speaker: \\"line\\"",
 "caption_brief": "one sentence describing the clip and its joke, for the caption writer",
 "uses_carrot": true or false,
 "trend_used": "which trend / format from the brief this uses, or 'none'",
 "story_summary": "one sentence: what happened in this clip (for the series log)",
 "cliffhanger": "if this clip leaves a storyline open, a 3-6 word teaser for the next part, else empty"
}"""


def write(state: dict, hint: str | None = None, note: str | None = None) -> dict:
    done = state.setdefault("concepts_done", [])
    brief = state.get("brief", {}).get("text", "")
    prompt = (RULES
              + (f"\nTREND BRIEF (this week's research and how our own posts performed):\n{brief}\n"
                 if brief else "")
              + f"\nRECENT EPISODES (newest last):\n{recent_story(state)}\n"
              + (f"\nThe previous clip ended on a cliffhanger ({state['story_log'][-1]['cliffhanger']}): "
                 "this clip MUST continue that storyline.\n"
                 if state.get("story_log") and state["story_log"][-1].get("cliffhanger") else "")
              + (f"\nAlready made (never repeat): {', '.join(done[-40:])}\n" if done else "")
              + (f"\nBuild the clip around this idea: {hint}\n" if hint else "")
              + (f"\nDirector's note (must follow): {note}\n" if note else "")
              + FORMAT)
    c = gen.text_json(prompt, prefer_pro=True)
    c["id"] = "concept-" + re.sub(r"[^a-z0-9-]", "", str(c.get("id", "clip")).lower())[:30]
    c["concept"] = True
    c["seconds"] = 10
    c["style"] = STYLE
    c["cast"] = [k for k in (c.get("cast") or []) if k in CAST]
    c["with_abu"] = "abu_lakma" in c["cast"]
    names = ". ".join(CAST[k] for k in c["cast"])
    c["look"] = ". ".join(x for x in (names, c.get("look") or "") if x)
    for k in ("demand", "bad_deal"):
        c.setdefault(k, "")
    c.setdefault("opponent", c.get("look", ""))
    log(f"concept: {c.get('title')} [{', '.join(c['cast']) or 'no cast'}; trend: "
        f"{c.get('trend_used', '-')}] - {c.get('caption_brief', '')}")
    return c


def remember(state: dict, c: dict, when: str):
    """Add a made clip to the series log so later clips can continue its storyline."""
    state.setdefault("concepts_done", []).append(c.get("title", ""))
    state.setdefault("story_log", []).append({
        "date": when, "title": c.get("title", ""), "summary": c.get("story_summary", ""),
        "cliffhanger": c.get("cliffhanger", "")})
    state["story_log"] = state["story_log"][-30:]


def script_text(c: dict) -> str:
    return (f"📜 **{c.get('title', '')}**\n**Setting:** {c.get('setting', '')}\n"
            f"**What happens:** {c.get('action', '')}\n**Sound:** {c.get('sound', '')}")[:1900]
