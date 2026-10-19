"""Turns an episode premise into a 4-shot cinematic comedy script for Veo."""
from . import gen
from .common import log

VOICE_TOUGH = ("very slow, deliberate, deep, raspy, quiet and menacing voice with a Brooklyn "
               "accent, long pauses between words, like an old mafia godfather")
VOICE_SOFT = "suddenly high-pitched, squeaky, sweet, baby-like voice"

# (name, seconds, Rappit's voice in this shot: tough / soft / None)
SHOTS = [
    ("THE DEMAND", 6, "tough"),
    ("THE COUNTER", 6, None),
    ("THE MELT", 6, "soft"),
    ("THE PAYOFF", 4, "soft"),
]

RULES = f"""
You are directing a short, dark, cinematic mafia-movie parody: a vertical short in exactly
4 shots. Star: Lil Rappit, a gangster rabbit (sunglasses, bucket hat, orange puffer, gold
chain) who is dead serious and intimidating. His ONE weakness is carrots.
The joke: a tense, serious negotiation, then a bag of carrots appears, his tough face melts,
and he happily accepts a TERRIBLE deal. The comedy comes from playing it completely
straight and dark until the melt.

Tone: classic crime drama. Low-key lighting, shadows, smoke-free haze, slow camera moves,
long silences, tension. Shot/reverse-shot between Rappit and the other character.

SHOT 1 "THE DEMAND" (6 s): starts MID-TENSION with no establishing pause: Rappit's first word
lands within the first second. Slow push-in on Rappit, medium close-up, the other character's
shoulder blurred in the foreground. Rappit states his demand clearly and SLOWLY, max 10
words, {VOICE_TOUGH}. Nobody else speaks.

SHOT 2 "THE COUNTER" (6 s): reverse shot on the other character, medium close-up over
Rappit's shoulder. They look nervous, swallow, then a slow sly smile. They slowly slide a
brown paper bag overflowing with fresh orange carrots across the table toward Rappit and say
the terrible deal OUT LOUD so it is unmistakable, max 14 words. Rappit does not speak.

SHOT 3 "THE MELT" (6 s): extreme close-up on Rappit's face, still dead serious. One beat of
silence. Then his face transforms in exaggerated physical comedy: sunglasses slowly slide
down his nose, eyes go huge and sparkly, ears shoot up then flop, nose twitches, lower lip
trembles. He accepts in a {VOICE_SOFT}, max 8 words, funny.

SHOT 4 "THE PAYOFF" (4 s): wide two-shot showing the terrible deal physically and clearly
(e.g. he pushes the briefcase of cash across, hands over the keys, signs the paper) while
hugging the carrot bag; the other character looks smug. No dialogue, or max 4 words.

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
    "action": "what happens during the shot, beat by beat, including camera movement",
    "dialogue": [{"speaker": "Rappit or the other character's name", "voice": "voice description", "line": "..."}]}
   ... exactly 4 shots in order ...
 ],
 "deal": "one sentence summary of the terrible deal, for the caption",
 "hook": "3-6 word on-screen hook shown in the first 3 seconds that makes people stay. Tease the tension, never spoil the carrots. Examples: 'NOBODY OUT-NEGOTIATES RAPPIT', 'HE NEVER TAKES A BAD DEAL', 'THE MOST FEARED RABBIT IN TOWN'"
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
    for d in shot.get("dialogue", []):
        who = d.get("speaker", "")
        voice = d.get("voice") or ""
        if who.lower().startswith(("rappit", "lil rappit")):
            voice = VOICE_SOFT if rappit_voice == "soft" else VOICE_TOUGH  # same voice every episode
        if d.get("line", "").strip():
            lines.append(f'{who} ({voice}): "{d["line"].strip()}"')
    return (
        f"Shot: {name}. Setting: {ep['setting']}.\n"
        f"Other character (looks exactly like this): {script.get('opponent_look', ep['opponent'])}.\n"
        f"Action: {shot['action']}\n"
        + ("Dialogue, spoken with lip sync:\n" + "\n".join(lines) + "\n" if lines
           else "No dialogue in this shot.\n")
        + "Only the listed lines are spoken. Tense, low cinematic score under the scene."
    )
