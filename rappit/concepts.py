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
ABU_FAHD = ("Abu Fahd, an original sly middle-aged red fox (realistic fur, not cartoon): a bit "
            "chubby, a big bushy grey-flecked moustache, sunglasses pushed up on his head, an "
            "unbuttoned burgundy paisley silk shirt, a gold medallion, black trousers, shiny "
            "pointed loafers, twirling a set of car keys on one finger")
UMM_LAKMA = ("Umm Lakma, Abu Lakma's wife: a stout no-nonsense bulldog with curlers in her hair, "
             "a purple house robe and pink fluffy slippers")
ABU_SLEIMAN = ("Abu Sleiman, the village mukhtar: an old white-bearded goat with a red tarboush, "
               "a grey wool vest over a white shirt and a wooden walking cane")
# Recurring cast (Rappit himself always uses the refs/ photos). Each keeps one reference image.
CAST = {"abu_lakma": ABU_LAKMA, "lola": LOLA, "teta": TETA, "abu_fahd": ABU_FAHD,
        "umm_lakma": UMM_LAKMA, "abu_sleiman": ABU_SLEIMAN}


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
You are the head writer of "Lil Rappit", a comedy series of short clips (exactly 10 seconds, one
continuous shot) for Instagram Reels and YouTube Shorts, for a Lebanese audience first. Think of the hit Iraqi AI series "Abu Saber & Abu Sarhan" (farm animals bickering
in heavy Iraqi dialect about village gossip, jealousy and small disasters), but Lebanese: a
village in the Bekaa (vineyards, a farm, stone houses, the village square, the dekkene, the
church/municipality steps, Sunday lunch at Teta's).

THE VILLAGE CAST (exact names; keep looks consistent):
- Lil Rappit: a gangster rabbit (black bucket hat, gold sunglasses, orange puffer jacket, gold
  chain with a carrot pendant). The village tough guy: dead serious, slow, raspy, intimidating,
  thinks he runs the village. Secret weakness: carrots.
- Abu Lakma: {ABU_LAKMA}. His loyal sidekick; big, simple, terrified of his wife.
- Umm Lakma: {UMM_LAKMA}. Abu Lakma's wife; she runs him (and sometimes Rappit).
- Lola: {LOLA}. Rappit's dramatic, glamorous girlfriend; jealous of carrots.
- Abu Fahd: {ABU_FAHD}. The sly charmer who keeps flirting with Lola: Rappit's rival.
- Teta: {TETA}. Rappit's grandmother; the only one he fears; she always wins.
- Abu Sleiman: {ABU_SLEIMAN}. The village mukhtar; knows everybody's business, spreads gossip.
EXACTLY TWO characters on screen per clip (Rappit + one other), no extras, no background crowd.
Drama continues across clips by pairing different characters (Rappit vs Abu Fahd today, Lola vs
Rappit next time).

LANGUAGE: everyone speaks natural Lebanese Arabic dialect (village/Bekaa flavour), never formal
Arabic, never English. Rappit always has lines.

WHAT MAKES IT FUNNY:
- QUICK BACK-AND-FORTH: 2-3 short lines total (max ~8 words each, it must fit in 10 seconds),
  ending on the punchline line or a reaction: insults with
  love, gossip, accusations, overreactions, threats that are obviously empty, Teta/mom logic,
  "inshallah" meaning no, "wlak", "ya 7aram", "walla", swearing on your mother, wasta, the
  cousin who knows a guy, everybody knows everybody's business.
- A recognisable village/family situation: who ate the last manoushe, the neighbour's chicken
  in your garden, Abu Fahd winking at Lola at the dekkene, the mukhtar announcing gossip,
  Umm Lakma catching Abu Lakma, the power cut during the match, the grape harvest, the wedding,
  the zaytoun, Sunday lunch, the shared water tank, parking a tractor.
- Rappit's mafia seriousness about petty things, and an ending punchline (a line + a reaction,
  someone staring into the camera, or Teta/Umm Lakma shutting everyone up).
- Drama arcs are welcome (Abu Fahd vs Rappit over Lola, Abu Lakma in trouble at home, a feud
  with the mukhtar): each clip must be funny on its own; it may end with the story open.
- The PUNCHLINE must land through a LINE and a FACE (a reaction, a look into the camera, a
  pause), never through precise physics the video model can't control (objects landing on
  heads, catching, throwing, biting things out of hands, liquids, crowds of small objects).
- At most ONE important prop, held in a character's hands from the first frame, big and
  simple (a cup, a phone, a plate). No tiny accessories doing anything.
- Simple physical action (mostly two characters talking, like a sitcom two-shot), one location,
  every prop visible from the first frame and named once with its count; each character wears
  only their own outfit.

NEVER: crime coding (stashes, deals, money exchanges, weapons, police); text on screen or
"Part X" in the video; smoking or argileh; alcohol; religion; politics; real people or
celebrities; real songs (describe the music style); romance beyond PG flirting and jealousy;
words like violent, aggressive, threaten, glare, snatch, shove, fight, slap, smash, attack,
blood, dead (the video filter blocks them; say firmly, warns, stares, grabs, pops, argues).
Carrots in at most 1 of 3 clips.
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
 "action": "[0-3s] SETUP ... [3-7s] the exchange ... [7-10s] PUNCHLINE + reaction; concrete actions and camera (mostly a steady two-shot)",
 "sound": "music style (instruments), ambience and sound effects only (dialogue goes in 'dialogue')",
 "dialogue": [{"speaker": "Rappit", "arabic": "the line in Lebanese Arabic, Arabic script", "arabizi": "the same line as Lebanese people write it in Latin letters", "english": "short English translation", "at": "e.g. 1-3s"}],
 "caption_brief": "one sentence: the relatable truth and the joke, for the caption writer",
 "uses_carrot": true or false,
 "story_summary": "one sentence: what happened",
 "cliffhanger": "if a drama arc stays open, a 3-6 word teaser for next time, else empty"
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
               + f"\nRECENT EPISODES (you MAY continue an open drama arc):\n{recent_story(state)}\n"
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
    c.pop("action_1", None)
    c.pop("action_2", None)
    c["cast"] = [k for k in (c.get("cast") or []) if k in CAST]
    c["with_abu"] = "abu_lakma" in c["cast"]
    names = ". ".join(CAST[k] for k in c["cast"])
    c["look"] = ". ".join(x for x in (names, c.get("look") or "") if x)
    for k in ("demand", "bad_deal"):
        c.setdefault(k, "")
    c.setdefault("opponent", c.get("look", ""))
    log(f"concept: {c.get('title')} [{', '.join(c['cast']) or 'no cast'}] - {c.get('joke', '')}")
    return c


PITCH = """Pitch {n} different 10-second village clip ideas, each with exactly two characters
(Rappit + one other), a quick 2-3 line Lebanese exchange and a real punchline that would make a
Lebanese viewer laugh and send it to a friend. Vary situations and partners; one may continue
or start a drama arc.
Return JSON: {{"ideas": [{{"title": "2-4 words", "cast": "who is in it",
"setup": "one sentence: the situation", "punchline": "one sentence: what is said/happens",
"rappit_line": "Rappit's key line in Lebanese (Latin letters)", "english": "its translation"}}]}}"""


def pitch(state: dict, theme: str | None = None, n: int = 5) -> list[dict]:
    done = state.get("concepts_done", [])
    brief = state.get("brief", {}).get("text", "")
    prompt = (RULES + (f"\nTREND BRIEF (inspiration only):\n{brief}\n" if brief else "")
              + (f"\nAlready made (never repeat): {', '.join(done[-40:])}\n" if done else "")
              + (f"\nTheme requested by the owner: {theme}\n" if theme else "")
              + PITCH.format(n=n))
    return gen.text_json(prompt, prefer_pro=True).get("ideas", [])[:n]


def remember(state: dict, c: dict, when: str):
    """Add a made clip to the log so the writer never repeats an idea."""
    state.setdefault("concepts_done", []).append(f"{c.get('title', '')}: {c.get('joke', '')}"[:160])
    state.setdefault("story_log", []).append({
        "date": when, "title": c.get("title", ""), "summary": c.get("story_summary", ""),
        "cliffhanger": c.get("cliffhanger", "")})
    state["story_log"] = state["story_log"][-30:]


def script_text(c: dict) -> str:
    return (f"📜 **{c.get('title', '')}**\n**The joke:** {c.get('joke', '')}\n"
            f"**Setting:** {c.get('setting', '')}\n"
            + "".join(f"> **{d.get('speaker', '')}:** {d.get('arabizi', '')} — *{d.get('english', '')}*\n"
                      for d in c.get("dialogue") or [])
            + f"**What happens:** {c.get('action', '')}\n**Sound:** {c.get('sound', '')}")[:1900]
