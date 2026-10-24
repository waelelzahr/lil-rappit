"""Turns an episode premise into a 4-shot cinematic comedy script for Veo."""
from . import gen
from .common import log

VOICE_TOUGH = ("slow, deliberate, deep, raspy, quiet and menacing voice with a Brooklyn "
               "accent, like an old mafia godfather")
VOICE_SOFT = "suddenly high-pitched, squeaky, sweet, baby-like voice"

# (name, seconds, Rappit's voice in this shot: tough / soft / None)
SHOTS = [
    ("THE DEMAND", 4, "tough"),
    ("THE COUNTER", 4, None),
    ("THE MELT", 6, "soft"),
]
# The reel opens with a flash of the melt (cut from shot 3) before shot 1: a cold open that
# makes scrollers ask "how does this guy end up like THAT?". It is cut around his squeaky
# "Carrots?" (found with word timestamps); these are the fallback (shot, start, length).
COLD_OPEN = (2, 2.4, 1.4)
COLD_OPEN_WORD = "carrot"

CATCHPHRASE = "Rappit don't do discounts."
HOOK_SUB = "Wait for his face"
# The bait shrinks / gets sillier every episode (escalation keeps the joke fresh).
BAITS = [
    "a brown paper bag overflowing with fresh orange carrots",
    "one single tiny baby carrot on a big silver plate",
    "a slice of carrot cake on a fancy dessert plate",
    "a small framed photo of a carrot",
    "a carrot-scented candle, lit",
    "a child's crayon drawing of a carrot on a napkin",
    "a gift card with a carrot printed on it",
    "a single carrot stick in a cocktail glass",
]
# Every 5th episode breaks the pattern.
TWISTS = [
    "TWIST: the carrot is obviously PLASTIC (the other character squeezes it and it squeaks) - "
    "Rappit sees it is fake and STILL melts and accepts",
    "TWIST: the paper bag is EMPTY - the other character just pretends there are carrots in it "
    "and Rappit still melts and accepts",
]


def flavor(no: int | None) -> tuple[str, str]:
    """(bait description, twist instruction or '') for episode number `no`."""
    n = no or 1
    if n % 5 == 4:
        twist = TWISTS[(n // 5) % len(TWISTS)]
        return ("a single orange carrot" if "PLASTIC" in twist else "an empty brown paper bag"), twist
    return BAITS[(n - 4) % len(BAITS)], ""  # episode 5 = baby carrot, then sillier

RULES = f"""
You are directing a short mafia-movie parody for Instagram Reels / YouTube Shorts, in exactly
3 shots (about 15 seconds in total). Star: Lil Rappit, a gangster rabbit (sunglasses, bucket hat, orange puffer, gold
chain) who is dead serious and intimidating. His ONE weakness is carrots.
The joke: a tense negotiation, then carrot bait appears, his tough face melts, and he
happily accepts a TERRIBLE deal. Played completely straight until the melt.

IT MUST BE FAST. Viewers decide in under 2 seconds whether to keep watching. Think crime-film
LOOK (hard light, shadows, haze, shot/reverse-shot) with meme PACING: no slow build-ups, no
silent establishing moments, every second something happens. Big, readable, exaggerated faces.
The situation should mirror an everyday thing people relate to (asking for a raise, a landlord,
a car salesman, a gym membership) so viewers send it to friends.
The terrible deal must be absurdly SPECIFIC: take the premise's bad deal and add one ridiculous
concrete detail (e.g. "the house, the car, AND grandma's soup recipe").
The bait this episode is: <<BAIT>>. <<TWIST>>

SHOT 1 "THE DEMAND" (4 s): Rappit is ALREADY TALKING in the very first frame - no pause,
  no walk-in. Close-up, slightly LOW ANGLE, 85mm, the other character's shoulder blurred in the
  foreground, a quick punchy push-in (not a slow dolly). ONE hard motivated light that fits the
  setting; half his face in shadow; sunglasses glint. His line ALWAYS starts with his catchphrase
  "{CATCHPHRASE}" and then states his demand clearly in max 5 more words, {VOICE_TOUGH} but
  without long pauses (it must fit in 4 seconds). Nobody else speaks.
  sound: low tense drone, one heavy bass hit on his last word.

SHOT 2 "THE COUNTER" (4 s): reverse shot, medium close-up on the other character over
  Rappit's blurred shoulder, a slow push-in. The other character says NOTHING - no dialogue at
  all. Hesitantly, they slide <<BAIT>> across the table toward Rappit while their eyes keep switching between Rappit's face and the
  floor: ashamed, embarrassed, not sure this ridiculous move will work. Awkward pause, a nervous
  swallow, a tiny unsure glance up at him.
  sound: the music drops out completely; only the bait scraping slowly across the table and
  a nervous gulp in an awkward silence.

SHOT 3 "THE MELT" (6 s): extreme close-up on Rappit, dead serious for half a second, then a
  HUGE over-the-top cartoon melt: sunglasses slide down his nose, eyes go enormous and sparkly
  and teary, ears shoot straight up then flop, nose twitches fast, cheeks blush, lower lip
  trembles. The face is at its most extreme from about second 2 to second 4. At about second 2
  he squeaks "Carrots?" and then accepts by saying the terrible deal himself so it is
  unmistakable, in a {VOICE_SOFT}, max 9 words in total, and the line MUST start with the word
  "Carrots?" (e.g. "Carrots? ...okay, the car is yours").
  In the last 2 seconds he DOES the deal on screen while clutching the bait (slides the keys /
  cash / signed paper across with one paw) as the camera pulls back to a two-shot, and the other
  character slowly turns and looks straight into the camera in stunned disbelief that it
  actually worked (like a mockumentary sitcom glance).
  sound: a heavenly "aaah" choir swell, a sparkle chime, a playful pizzicato sting at the end.

Wording: never use words like violent, slap, smash, attack, threatening, blood or weapon in any
field (the image and video models refuse them); say sudden, fast, dramatic, plops down instead.
Constraints for the video model: same location in every shot, the same two characters,
simple clear actions, no text on screen, family-friendly, no smoking, no weapons.
"""


def write_script(ep: dict, note: str | None = None, no: int | None = None) -> dict:
    bait, twist = flavor(no)
    prompt = (
        RULES.replace("<<BAIT>>", bait).replace("<<TWIST>>", twist)
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
   ... exactly 3 shots in order ...
 ],
 "relatable": "the everyday situation this parodies, e.g. asking your boss for a raise",
 "deal": "one sentence summary of the terrible deal, for the caption",
 "hook": "3-6 word on-screen hook shown in the first 3 seconds over Rappit's melted face while he squeaks 'Carrots?'. It must build him up as fearsome so the picture ironically contradicts it. Examples: 'THE MOST FEARED NEGOTIATOR IN TOWN', 'HE HAS NEVER LOST A DEAL', 'THE MAFIA FEARS THIS RABBIT', 'NOBODY OUT-NEGOTIATES HIM'. Vary it every episode."
}"""
    )
    script = gen.text_json(prompt, prefer_pro=True)
    if len(script.get("shots", [])) != len(SHOTS):
        raise ValueError(f"writer returned {len(script.get('shots', []))} shots, expected {len(SHOTS)}")
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
