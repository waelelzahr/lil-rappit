# YouTube API Services – Audit form answers (Rappit Studio)

Form: https://support.google.com/youtube/contact/yt_api_form
Choose: **"I want to have my API client audited"** (no quota increase needed).
Fill in the bracketed bits [ ] yourself.

---

## Organization / contact
- **Organization name:** Lil Rappit (individual creator)
- **Organization website:** https://www.instagram.com/lilrappit/
- **Your name:** Wael El Zahr
- **Contact email:** (owner contact email)
- **Address / country:** [your address], Lebanon

## API project
- **Google Cloud project name:** Rappit Studio
- **Project number / ID:** [Cloud Console → project picker → copy both]
- **OAuth client ID:** [the YT_CLIENT_ID value]
- **YouTube channel(s) used:** Lil Rappit – https://youtube.com/channel/UCRg-VDB8ARE88O1p-XgTSGg

## API client description
- **Name of API client:** Rappit Studio
- **Type:** Internal/private tool (server-side scheduled job). Not offered to the public, no other users.
- **Short description (paste as-is):**

> Rappit Studio is a private publishing tool used only by me, the owner of the "Lil Rappit" YouTube channel. It runs as a scheduled job in my private GitHub repository. Each week it prepares short comedy videos featuring my original animated character, Lil Rappit. I review and approve every video by hand before anything is published. At the scheduled time, the tool uploads the approved video to my own channel as a YouTube Short using videos.insert, with a title and description and the synthetic-media (AI) disclosure flag set.
>
> The tool only accesses my own channel, using OAuth 2.0 with my own Google account. It does not access, collect, store or share data from any other YouTube users or viewers. It does not download, re-host or modify other people's content, and it does not read analytics, comments or subscriber data.

- **APIs and methods used:**
  - YouTube Data API v3 – `videos.insert` (upload own Shorts)
  - YouTube Data API v3 – `channels.list` (mine=true, to confirm the connected channel)
- **OAuth scopes:** `youtube.upload`, `youtube.readonly`
- **Expected usage:** 1–3 uploads per week (well within the default 10,000 units/day; no quota increase requested)
- **Number of users:** 1 (the channel owner)
- **Does the client display YouTube data to users?** No
- **Does it store YouTube API data?** Only the ID and URL of my own uploaded videos, so the tool can tell me where each one was posted.
- **Privacy policy:** https://docs.google.com/document/d/1trUDQNHBvHp1p3DGQAjpUVIIIsp3PAtNPm7z9HUZ09o/view
- **Terms of service:** N/A (private tool, single user)

## Why I'm requesting the audit
> Videos uploaded through my unverified API project are locked to private. I'm asking for an audit so that my own approved Shorts can be published with the visibility I choose (public), the same as uploading them manually in YouTube Studio.

## Compliance confirmations
Tick the boxes confirming compliance with the YouTube API Services Terms of Service and Developer Policies.

## Screenshots / demo (if asked)
Attach 2–3 screenshots:
1. The Discord review channel showing a draft with ✅ / 🔁 (shows a human approves each upload)
2. The "🚀 Posted on YouTube" confirmation message
3. The uploaded Short in YouTube Studio showing the "Altered or synthetic content" label
