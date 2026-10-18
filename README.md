# Lil Rappit pipeline

Weekly comedy content for Lil Rappit, generated with the Gemini API and approved on Telegram.

**Every Sunday 09:00 (Beirut)** the *Weekly drafts* workflow:
1. picks a random unused episode from `episodes.yaml`
2. generates a 16 s reel (two 8 s Veo 3.1 Fast clips, stitched), a mugshot photo and a soft-side photo, using `refs/` + `character.md` for consistency
3. sends each draft to Telegram with **Approve / Redo** buttons

**Every hour (08:00–23:00)** the *Review replies* workflow reads your taps:
- ✅ Approve → queued for its posting slot (see `config.yaml`)
- 🔁 Redo → regenerated (max 3 per item)
- Reply to a draft with text → regenerated using your note, e.g. "make the cop a crocodile"

Posting to Instagram Reels and YouTube Shorts is added in a later step.

## Secrets (repo Settings → Secrets and variables → Actions)
| Name | What |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key (paid tier) |
| `TELEGRAM_BOT_TOKEN` | from @BotFather |
| `TELEGRAM_CHAT_ID` | your chat id with the bot |

## Editing
- New gags: add entries to `episodes.yaml`
- Look/personality: `character.md` and `rappit/gen.py` (`LOOK`)
- Models, schedule, caps: `config.yaml`
- Run now: Actions tab → workflow → *Run workflow*
