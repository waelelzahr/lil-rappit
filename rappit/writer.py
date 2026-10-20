"""Turns an episode premise into a 4-shot cinematic comedy script for Veo."""
from . import gen
from .common import log

VOICE_TOUGH = ("slow, deliberate, deep, raspy, quiet and menacing voice with a Brooklyn "
               "accent, like an old mafia godfather")
VOICE_SOFT = "suddenly high-pitched, squeaky, sweet, baby-like voice"

# (name, seconds, Rappit's voice in this shot: tough / soft / None)
SHOTS = [
    ("THE DEMAND", 4, "tough"),
    ("THE COUNTER", 6, None),
    ("THE MELT", 6, "soft"),
    ("THE PAYOFF", 4, "soft"),
]
# The reel opens with a 1 s flash of the melt (cut from shot 3) before shot 1: a cold open
# that makes scrollers ask "how does this guy end up like THAT?".
COLD_OPEN = (2, 4.2, 1.2)  # (shot index, start second, length)

RULES = f"""
You are directing a short mafia-movie parody for Instagram Reels / YouTube Shorts, in exactly
4 shots. Star: Lil Rappit, a gangster rabbit (sunglasses, bucket hat, orange puffer, gold
chain) who is dead serious and intimidating. His ONE weakness is carrots.
The joke: a tense negotiation, then a bag of carrots appears, his tough face melts, and he
happily accepts a TERRIBLE deal. Played completely straight until the melt.

IT MUST BE FAST. Viewers decide in under 2 seconds whether to keep watching. Think crime-film
LOOK (hard light, shadows, haze, shot/reverse-shot) with meme PACING: no slow build-ups, no
silent establishing moments, every second something happens. Big, readable, exaggerated faces.
The situation should mirror an everyday thing people relate to (asking for a raise, a landlord,
a car salesman, a gym membership) so viewers send it to friends.

SHOT 1 "THE DEMAND" (4 s): Rappit is ALREADY TALKING in the very first frame - no pause,
  no walk-in. Close-up, slightly LOW ANGLE, 85mm, the other character's shoulder blurred in the
  foreground, a quick punchy push-in (not a slow dolly). ONE hard motivated light that fits the
  setting; half his face in shadow; sunglasses glint. He states his demand clearly, max 8 words,
  {VOICE_TOUGH} but without long pauses (it must fit in 4 seconds). Nobody else speaks.
  sound: low tense drone, one heavy bass hit on his last word.

SHOT 2 "THE COUNTER" (6 s): reverse shot, medium close-up on the other character over
  Rappit's blurred shoulder, a slow push-in. The other character says NOTHING - no dialogue at
  all. Slowly, hesitantly, they slide a brown paper bag overflowing with fresh orange carrots
  across the table toward Rappit while their eyes keep switching between Rappit's face and the
  floor: ashamed, embarrassed, not sure this ridiculous move will work. Awkward pause, a nervous
  swallow, a tiny unsure glance up at him.
  sound: the music drops out completely; only the paper bag scraping slowly across the table and
  a nervous gulp in an awkward silence.

SHOT 3 "THE MELT" (6 s): extreme close-up on Rappit, dead serious for half a second, then a
  HUGE over-the-top cartoon melt: sunglasses slide down his nose, eyes go enormous and sparkly
  and teary, ears shoot straight up then flop, nose twitches fast, cheeks blush, lower lip
  trembles, paws clasp under his chin. The face must be at its most extreme from about
  second 3.5 to second 5.5. He accepts by saying the terrible deal himself so it is unmistakable,
  in a {VOICE_SOFT}, max 8 words, funny (e.g. "okay... the car is yours").
  sound: a heavenly "aaah" choir swell and a sparkle chime.

SHOT 4 "THE PAYOFF" (4 s): wide two-shot showing the terrible deal physically and clearly
  (he pushes the cash across, hands over the keys, signs the paper) while hugging the carrot bag;
  the other character looks smug. END on Rappit's blissed-out melted face pushing into a close-up
  (so the end loops back into the opening flash). No dialogue, or max 3 words.
  sound: a playful pizzicato sting.

Wording: never use words like violent, slap, smash, attack, threatening, blood or weapon in any
field (the image and video models refuse them); say sudden, fast, dramatic, plops down instead.
Constraints for the video model: same location in every shot, the same two characters,
simple clear actions, no text on screen, family-friendly, no smoking, no weapons.
"""


def write_script(ep: dict, note: str | None = None) -> dict:
    prompt = (
        RULES
        + f"\nPremise: \"{ep['title']}\"\nSetting: {ep['setting']}\nOther character: {ep['opponent']}\n"
        + f"Rappit's demand: {ep['demand']}\nThe terrible deal he accepts: {ep['bad_deal']}\n"
        + (f"\nDirector's note (must follow): {note}\n" if note else "")
        + """
Return JSON:
{
 "opponent_look": "detailed visual description of the other character (species, clothes, colors, face) so they look identical in every shot",
 "shots": [
   {"frame": "the opening still of this shot: framing, who is visible, props, lighting",
    "camera": "lens, angle and exact camera movement",
    "lighting": "light sources, shadows, haze, color",
    "performance": "facial expressions, body language and timing, beat by beat",
    "sound": "music, ambience and sound effects",
    "action": "what happens during the shot, beat by beat",
    "dialogue": [{"speaker": "Rappit or the other character's name", "voice": "voice description", "line": "..."}]}
   ... exactly 4 shots in order ...
 ],
 "relatable": "the everyday situation this parodies, e.g. asking your boss for a raise",
 "deal": "one sentence summary of the terrible deal, for the caption",
 "hook": "4-9 word on-screen hook shown in the first 3 seconds. It is shown over a 1-second flash of Rappit's melted face, so it must make that face relatable and shareable, meme style ('POV:' / 'Me when...'). Examples: 'ME WHEN HR SAYS PIZZA PARTY', 'POV: YOUR LANDLORD BROUGHT SNACKS', 'ME AT THE DEALERSHIP WHEN THEY OFFER FREE FLOOR MATS'"
}"""
    )
    script = gen.text_json(prompt, prefer_pro=True)
    if len(script.get("shots", [])) != len(SHOTS):
        raise ValueError(f"writer returned {len(script.get('shots', []))} shots, expected 4")
    log(f"script: {script.get('deal', '')}")
    return script


def shot_prompt(ep: dict, script: dict, idx: int) -> str:
    name, _, rappit_voice = SHOTS[idx]
    shot = script["shots"][idx]
    lines = []
    for d in ([] if idx == 1 else shot.get("dialogue", [])):  # shot 2 is silent by design
        who = d.get("speaker", "")
        voice = d.get("voice") or ""
        if who.lower().startswith(("rappit", "lil rappit")):
            voice = VOICE_SOFT if rappit_voice == "soft" else VOICE_TOUGH  # same voice every episode
        if d.get("line", "").strip():
            lines.append(f'{who} ({voice}): "{d["line"].strip()}"')
    return (
        f"Shot: {name}. Setting: {ep['setting']}.\n"
        f"Other character (looks exactly like this): {script.get('opponent_look', ep['opponent'])}.\n"
        f"Camera: {shot.get('camera', '')}\n"
        f"Lighting: {shot.get('lighting', '')}\n"
        f"Performance: {shot.get('performance', '')}\n"
        f"Action: {shot['action']}\n"
        f"Sound design: {shot.get('sound', '')}\n"
        + ("Dialogue, spoken with lip sync:\n" + "\n".join(lines) + "\n" if lines
           else "No dialogue in this shot.\n")
        + "Only the listed lines are spoken. The first line starts immediately at the very first frame, "
        "no silent lead-in. Expressive, exaggerated acting and snappy pacing with no dead air."
    )


def readable(script: dict, title: str = "") -> str:
    """The script as plain Markdown, for Discord and the repo."""
    out = [f"# {title}" if title else "# Script",
           f"**Hook:** {script.get('hook', '')}",
           f"**Deal:** {script.get('deal', '')}",
           f"**Opponent:** {script.get('opponent_look', '')}", ""]
    for i, (name, secs, _) in enumerate(SHOTS):
        sh = script["shots"][i]
        out.append(f"## Shot {i + 1} · {name} ({secs}s)")
        for key in ("frame", "camera", "lighting", "action", "performance", "sound"):
            if sh.get(key):
                out.append(f"- *{key.capitalize()}:* {sh[key]}")
        for d in sh.get("dialogue", []):
            if d.get("line", "").strip():
                out.append(f"> **{d.get('speaker', '')}:** \"{d['line'].strip()}\"")
        out.append("")
    return "\n".join(out)


def dialogue_only(script: dict) -> str:
    """Short version for Discord: hook, lines per shot, deal."""
    out = [f"📜 **Script** · hook: *{script.get('hook', '')}*"]
    for i, (name, secs, _) in enumerate(SHOTS):
        sh = script["shots"][i]
        lines = [f"> **{d.get('speaker', '')}:** {d['line'].strip()}"
                 for d in sh.get("dialogue", []) if d.get("line", "").strip()]
        what = (sh.get("action") or "").strip()
        out.append(f"**{i + 1}. {name}** ({secs}s): {what[:220]}")
        out += lines or ["> *(no dialogue)*"]
    out.append(f"🥕 **Deal:** {script.get('deal', '')}")
    return "\n".join(out)
