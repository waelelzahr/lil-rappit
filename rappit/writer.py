"""Turns an episode premise into a tight 2-shot comedy script for Veo."""
from . import gen
from .common import log

VOICE_TOUGH = "deep, slow, raspy gangster voice with a thick Brooklyn accent, like an old mob boss"
VOICE_SOFT = "suddenly high-pitched, squeaky, sweet, baby-like voice"

RULES = f"""
You are a comedy director writing a 16-second vertical short in exactly two 8-second shots.
Star: Lil Rappit, a tough gangster rabbit (sunglasses, bucket hat, orange puffer, gold chain)
whose ONE weakness is carrots. The joke every time: tough-guy negotiation -> a bag of carrots
appears -> his face melts -> he happily accepts a TERRIBLE deal.

SHOT 1 (0-8 s) "The Squeeze": medium two-shot across a table/desk/counter. Rappit is
menacing and in control; the opponent is nervous. Rappit makes his tough demand in ONE
short line ({VOICE_TOUGH}). The opponent can answer with one short nervous line.
End on Rappit leaning in, intimidating. Max 18 spoken words in the shot.

SHOT 2 (8-16 s) "The Carrot": starts on a CLOSE-UP of Rappit's face, still tough, sunglasses on.
The opponent's paw slowly slides a brown paper bag overflowing with fresh orange carrots across
the table into frame. One beat of silence. Then his face visibly transforms in exaggerated
cartoon-like physical comedy: sunglasses slide down his nose, eyes go huge and sparkly,
ears shoot straight up then flop down, nose twitches, lower lip trembles.
The opponent says the terrible deal OUT LOUD so it is unmistakable (one short line).
Rappit answers in a {VOICE_SOFT}: a short, funny acceptance. He also SHOWS the bad deal
with a clear physical action (e.g. pushes the briefcase of cash over, hands over keys,
signs the paper), hugging the carrot bag. Max 18 spoken words in the shot.

Constraints for the video model: one location, at most two characters, simple clear actions,
describe camera framing, no text on screen, family-friendly, no smoking, no weapons.
"""


def write_script(ep: dict, note: str | None = None) -> dict:
    prompt = (
        RULES
        + f"\nPremise: \"{ep['title']}\"\nSetting: {ep['setting']}\nOpponent: {ep['opponent']}\n"
        + f"Rappit's tough demand: {ep['demand']}\nThe terrible deal he accepts: {ep['bad_deal']}\n"
        + (f"\nDirector's note (must follow): {note}\n" if note else "")
        + """
Return JSON:
{
 "shot1": {"frame": "the opening still: composition, both characters, props, lighting",
           "action": "what happens during the 8 seconds, beat by beat, with camera",
           "dialogue": [{"speaker": "Rappit or opponent name", "voice": "voice description", "line": "..."}]},
 "shot2": {"frame": "the close-up opening still of shot 2",
           "action": "...", "dialogue": [...]},
 "deal": "one sentence summary of the terrible deal, for the caption"
}"""
    )
    script = gen.text_json(prompt, prefer_pro=True)
    log(f"script: {script.get('deal', '')}")
    return script


def shot_prompt(ep: dict, shot: dict, soft: bool = False) -> str:
    lines = []
    for d in shot.get("dialogue", []):
        who = d.get("speaker", "")
        voice = d.get("voice") or ""
        if who.lower().startswith(("rappit", "lil rappit")):
            voice = VOICE_SOFT if soft else VOICE_TOUGH  # same voice every episode
        lines.append(f'{who} ({voice}): "{d.get("line", "").strip()}"')
    return (
        f"Setting: {ep['setting']}. Other character: {ep['opponent']}.\n"
        f"Action: {shot['action']}\n"
        + ("Dialogue, spoken clearly with lip sync:\n" + "\n".join(lines) + "\n" if lines else "")
        + "Comedic timing, expressive faces, cinematic. Only the listed lines are spoken."
    )
