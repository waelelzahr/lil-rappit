"""New format: one ~10 s clip per post. Lil Rappit (tough, deadpan gangster rabbit) and his
sidekick Abu Lakma in Lebanese / Arab everyday life, music- and visual-driven comedy.
The writer invents a fresh concept each time (same fields as concepts.yaml)."""
import json
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
TETA = ("Teta, Rappit's tiny strict grandmother: an old silver-grey rabbit wearing ONE pair of "
        "round gold glasses on her nose, hair in a neat bun, floral house dress, beige cardigan "
        "and slippers")
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
You are the head comedy writer of "Lil Rappit", a series of short clips (exactly 10 seconds,
one continuous shot) for Instagram Reels and YouTube Shorts. Audience: Lebanese and Arab viewers
first, but anyone should get it. Goal: people laugh, SEND it to a friend ("this is literally my
family") and follow.

CAST (exact names, consistent looks):
- Lil Rappit: a tough gangster rabbit (black bucket hat, gold sunglasses, orange puffer jacket,
  gold chain with a carrot pendant). Always dead serious and intimidating. The comedy engine is
  his deadpan tough-guy attitude colliding with ordinary Lebanese life. Secret weakness: carrots.
- Abu Lakma: {ABU_LAKMA}. His loyal sidekick, the straight man who stares into the camera.
- Lola: {LOLA}. His dramatic, glamorous girlfriend, jealous of carrots. Occasional.
- Teta: {TETA}. His grandmother, the only one he fears; she always wins. Occasional.

OUR BEST CLIP (the model to follow): Rappit and Abu Lakma lead a dabke line at a village wedding
to mijwiz music, deadly serious; Rappit does extreme dabke squats; a grandma at the edge of the
dance floor waves a carrot she is holding; Rappit abandons the dance mid-step and runs to her;
Abu Lakma is left alone mid-step and stares into the camera.
Why it works: (1) everyone recognises the situation, (2) Rappit treats it with absurd mafia
seriousness, (3) ONE clear, visible punchline at the end, (4) no words needed.

EVERY CLIP MUST HAVE:
- A RELATABLE TRUTH: a specific, universally recognised Lebanese / Arab moment (the Lebanese
  goodbye that lasts an hour, Teta forcing food, the power cut mid-something, the generator guy,
  service taxis that keep stopping, haggling at the souk, Sunday lunch, wedding dabke, the coffee
  cup reading, the mom who knows everything, tawleh trash talk, the zaytoun harvest, the
  neighbour who hears everything, the Arab mom's 'ma fi akl bel bayt'...).
- ONE JOKE you can say in one sentence, built as SETUP (0-3s: the recognisable situation is clear
  immediately) -> ESCALATION (3-7s: Rappit's tough-guy approach makes it bigger) -> PAYOFF
  (7-10s: one clear, visible, surprising punchline + a reaction, often a stare into the camera).
- It is funny with the sound off and for someone who never saw another episode.
- Simple physical action, one location, max 3 characters, every prop visible from the first
  frame (nothing appears out of nowhere). In "frame", name every object ONCE with its count
  ("one coffee cup on the table") and never put two of the same thing in the scene unless the
  joke needs it. Each character wears only their own outfit and accessories.

NEVER:
- Random chains of events, plot twists for their own sake, or "lore" (stashes, swaps, heists,
  betrayals). No crime coding: no briefcases of money, deals, stashes, drugs, cash exchanges,
  police, weapons, or anything that looks like a crime (the video model blocks it).
- Text on screen, "Part X" in the video, subtitles.
- Smoking or argileh, alcohol, religion, politics, real people or celebrities, real songs
  (describe the music style), romance beyond PG.
- Words like violent, slap, smash, attack, threatening, blood.
- Carrots in more than 1 of 3 clips.
"""

IDEAS = """
Brainstorm 8 different clip ideas. For each give: relatable_truth, joke (one sentence, setup ->
payoff), why_funny, and scores 1-10 for relatable, funny, clear_without_words, visual_payoff.
Then choose the single best one (highest total; break ties toward the most relatable).
Return JSON: {"ideas": [...], "best": <index of best idea>}"""

FORMAT = """
Write the chosen idea as the clip. Return JSON:
{
 "id": "short-kebab-case-id",
 "title": "2-4 word title",
 "relatable_truth": "the recognisable moment, in one sentence",
 "joke": "the joke in one sentence (setup -> payoff)",
 "cast": ["abu_lakma", "lola", "teta"] (only recurring characters who appear; can be empty),
 "look": "visual description of any NEW one-off characters (animal characters, clothes, colors), or empty string",
 "setting": "one vivid Lebanese location, time of day, lighting, background details",
 "frame": "the opening still: framing, who stands where, what each holds (every prop that will be used must already be visible)",
 "action": "[0-3s] SETUP ... [3-7s] ESCALATION ... [7-10s] PAYOFF ... concrete physical actions and camera moves",
 "sound": "music style (instruments), ambience, effects, and at most one or two tiny lines as Speaker: \"line\" (Lebanese Arabic in Latin letters welcome)",
 "caption_brief": "one sentence: the relatable truth and the joke, for the caption writer",
 "uses_carrot": true or false,
 "story_summary": "one sentence: what happened",
 "cliffhanger": ""
}"""

CRITIC = """You are a tough comedy editor. Rate this 10-second clip script for Instagram Reels:
{script}
Score 1-10: relatable (instantly recognisable Lebanese/Arab moment), funny (would a Lebanese
viewer laugh and send it to a friend?), clear (understood with sound off, single joke, nothing
random), feasible (a video model can render it: simple actions, props visible, no crime coding){premise}.
Return JSON: {{"scores": {{"relatable": n, "funny": n, "clear": n, "feasible": n, "premise": n}},
"verdict": "pass" if every score >= 7 else "rewrite", "fix": "one concrete instruction to make it
funnier, clearer and easier to render, keeping the premise"}}
(Leave "premise" out if no premise was given.)"""


def write(state: dict, hint: str | None = None, note: str | None = None) -> dict:
    done = state.setdefault("concepts_done", [])
    brief = state.get("brief", {}).get("text", "")
    context = (RULES
               + (f"\nTHIS WEEK'S TREND BRIEF (inspiration only; the rules above win):\n{brief}\n"
                  if brief else "")
               + (f"\nAlready made (never repeat these ideas): {', '.join(done[-40:])}\n" if done else "")
               + (f"\nMANDATORY PREMISE (from the show's owner; every idea, draft and rewrite must "
                  f"be exactly this situation with these characters): {hint}\n" if hint else "")
               + (f"\nDirector's note (must follow): {note}\n" if note else ""))
    # 1) brainstorm and pick the strongest joke
    try:
        ideas = gen.text_json(context + IDEAS, prefer_pro=True)
        best = ideas["ideas"][int(ideas.get("best", 0))]
        pick = (f"\nCHOSEN IDEA: {best.get('joke')} (relatable truth: {best.get('relatable_truth')}; "
                f"why funny: {best.get('why_funny')})\n")
        log(f"idea picked: {best.get('joke')}")
    except Exception as e:
        log(f"brainstorm failed, writing directly: {e}")
        pick = ""
    # 2) write it, then 3) let an editor push back once
    c = gen.text_json(context + pick + FORMAT, prefer_pro=True)
    try:
        review = gen.text_json(CRITIC.format(
            script=json.dumps(c, ensure_ascii=False),
            premise=(f", premise (it must be exactly this: {hint}; score 1 if not)" if hint else "")),
            prefer_pro=True)
        log(f"editor: {review.get('scores')} {review.get('verdict')}")
        if review.get("verdict") != "pass":
            c = gen.text_json(context + pick + f"\nEDITOR'S NOTE ON YOUR DRAFT {json.dumps(c, ensure_ascii=False)}: "
                              f"{review.get('fix')}\nRewrite it.\n" + FORMAT, prefer_pro=True)
    except Exception as e:
        log(f"editor pass skipped: {e}")
    c["id"] = "concept-" + re.sub(r"[^a-z0-9-]", "", str(c.get("id", "clip")).lower())[:30]
    c["concept"] = True
    c["seconds"] = 10
    c["style"] = STYLE
    c["cliffhanger"] = ""  # standalone clips; no "Part 2" chains
    c["cast"] = [k for k in (c.get("cast") or []) if k in CAST]
    c["with_abu"] = "abu_lakma" in c["cast"]
    names = ". ".join(CAST[k] for k in c["cast"])
    c["look"] = ". ".join(x for x in (names, c.get("look") or "") if x)
    for k in ("demand", "bad_deal"):
        c.setdefault(k, "")
    c.setdefault("opponent", c.get("look", ""))
    log(f"concept: {c.get('title')} [{', '.join(c['cast']) or 'no cast'}] - {c.get('joke', '')}")
    return c


def remember(state: dict, c: dict, when: str):
    """Add a made clip to the log so the writer never repeats an idea."""
    state.setdefault("concepts_done", []).append(f"{c.get('title', '')}: {c.get('joke', '')}"[:160])
    state.setdefault("story_log", []).append({
        "date": when, "title": c.get("title", ""), "summary": c.get("story_summary", ""),
        "cliffhanger": ""})
    state["story_log"] = state["story_log"][-30:]


def script_text(c: dict) -> str:
    return (f"📜 **{c.get('title', '')}**\n**The joke:** {c.get('joke', '')}\n"
            f"**Setting:** {c.get('setting', '')}\n"
            f"**What happens:** {c.get('action', '')}\n**Sound:** {c.get('sound', '')}")[:1900]
