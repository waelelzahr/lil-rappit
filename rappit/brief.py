"""Weekly research: what is trending in short-form comedy + how our own posts did.
The distilled brief is stored in state["brief"] and fed to the concept writer."""
from datetime import datetime

from . import gen, insights
from .common import TZ, log

QUESTION = """Research, using live web search, what is going viral RIGHT NOW (the last 2-3 weeks)
in short-form comedy video on TikTok, Instagram Reels and YouTube Shorts. Focus on:
1. Comedy formats, meme templates and trends people are copying this week (globally).
2. What is trending in Lebanon and the Arab world (memes, sounds, seasonal moments, events,
   holidays and occasions in the next 2 weeks).
3. What AI-generated character / animal comedy accounts are doing that gets millions of views
   (formats, recurring characters, drama series, hooks).
For each item: what it is, why it works, and how a tough deadpan gangster rabbit character with
a bulldog sidekick, a dramatic girlfriend and a strict grandmother could use it in a 10-second
clip. Skip anything involving real celebrities, politics, religion, weapons or smoking."""

DISTILL = """You prepare the weekly creative brief for the "Lil Rappit" comedy clip series.

WEB RESEARCH:
{research}

OUR OWN POSTS (newest first; views, shares, saves and watch time tell us what sticks):
{stats}

Write a compact brief (max 250 words) as JSON with key "text": a bullet list covering
(a) 4-6 specific trends / formats / occasions to use this week and how,
(b) what our numbers say works and what flops (be concrete: which clips and why),
(c) 2-3 things to avoid. Then key "summary": 3 short lines for the account owner."""


def build(state: dict) -> dict:
    try:
        research = gen.research(QUESTION)
    except Exception as e:
        log(f"trend research failed: {e}")
        research = "(web research unavailable this week)"
    stats = insights.summary()
    try:
        b = gen.text_json(DISTILL.format(research=research[:12000], stats=stats[:6000]),
                          prefer_pro=True)
        text = b.get("text")
        text = "\n".join(text) if isinstance(text, list) else str(text or "")
        summary = b.get("summary")
        summary = "\n".join(summary) if isinstance(summary, list) else str(summary or "")
    except Exception as e:
        log(f"brief distill failed: {e}")
        text, summary = research[:2000], "Trend research done (raw)."
    state["brief"] = {"date": datetime.now(TZ).strftime("%Y-%m-%d"), "text": text,
                      "summary": summary, "stats": stats[:4000]}
    log(f"brief: {summary}")
    return state["brief"]
