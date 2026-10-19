# Lil Rappit pipeline

Weekly comedy content for Lil Rappit, generated with the Gemini API and approved in Discord.

**Every Sunday 09:00 (Beirut)** the *Weekly drafts* workflow:
1. picks a random unused episode from `episodes.yaml`
2. for each of the 2 weekly reels, writes a 4-shot script and generates a ~22 s dark cinematic reel (four Veo 3.1 Fast shots, stitched), adds a hook and burned-in captions, plus a mugshot photo and a soft-side photo, using `refs/` + `character.md` for consistency
3. posts each draft in your private Discord channel with ✅ / 🔁 reactions

**Every 30 minutes (08:00–24:00)** the *Review replies* workflow checks Discord:
- tap ✅ → approved, queued for its posting slot (see `config.yaml`)
- tap 🔁 → regenerated (max 3 per item)
- reply to a draft with a note → regenerated using it, e.g. "make the cop a crocodile"
- type `status` → shows the queue

**Google's daily Veo limit** (10 videos/day on Tier 1) is tracked: a reel (4 videos) only starts if it can finish, reel 2 is made on Wednesday, and anything that doesn't fit waits in a queue until after Google's daily reset (~10:05 Beirut). Type `status` in Discord to see the queue and how many videos are left today.

## Secrets (repo Settings → Secrets and variables → Actions)
| Name | What |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key (paid tier) |
| `DISCORD_BOT_TOKEN` | Discord Developer Portal → your app → Bot → Reset Token |
| `DISCORD_CHANNEL_ID` | right-click your channel → Copy Channel ID (Developer Mode on) |

## Editing
- New gags: add entries to `episodes.yaml`
- Look/personality: `character.md` and `rappit/gen.py` (`LOOK`)
- Models, schedule, caps: `config.yaml`
- Run now: Actions tab → workflow → *Run workflow*
