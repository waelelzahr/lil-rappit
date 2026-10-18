# Lil Rappit pipeline

Weekly comedy content for Lil Rappit, generated with the Gemini API and approved by email.

**Every Sunday 09:00 (Beirut)** the *Weekly drafts* workflow:
1. picks a random unused episode from `episodes.yaml`
2. generates a 16 s reel (two 8 s Veo 3.1 Fast clips, stitched), a mugshot photo and a soft-side photo, using `refs/` + `character.md` for consistency
3. emails each draft to you

**Every hour (08:00–23:00)** the *Review replies* workflow reads your email replies:
- **OK** → approved, queued for its posting slot (see `config.yaml`)
- **REDO** → regenerated (max 3 per item)
- Any other text → regenerated using your note, e.g. "make the cop a crocodile"

Posting to Instagram Reels and YouTube Shorts is added in a later step.

## Secrets (repo Settings → Secrets and variables → Actions)
| Name | What |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key (paid tier) |
| `EMAIL_ADDRESS` | your Gmail address (drafts are sent to and from it) |
| `EMAIL_APP_PASSWORD` | Gmail app password (Google Account → Security → App passwords) |

## Editing
- New gags: add entries to `episodes.yaml`
- Look/personality: `character.md` and `rappit/gen.py` (`LOOK`)
- Models, schedule, caps: `config.yaml`
- Run now: Actions tab → workflow → *Run workflow*
