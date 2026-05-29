# Data handling & privacy notes

A factual map of what the bot stores and which third parties it sends data
to — the input a client's privacy policy / DPA and any GDPR assessment
would build on. **Not legal advice**; have counsel review before selling.

## What is stored, and where

All persistent data is local to the deployment (no app database server):

| Data | Location | Purpose | Notes |
|---|---|---|---|
| Delivered post IDs | `user_settings.json` | skip-already-seen, /unread | Capped at 5000, IDs only. |
| Bookmarks (+ tags) | `user_settings.json` | /bookmarks | Post IDs + user tags. |
| Preferences | `user_settings.json` | voice, language, filters, channel, auto-scrape, `chat_id` for scheduled jobs | The auto-scrape config stores the chat_id it posts to. |
| Article history | `history.db` | /find, /stats | Title + first 500 chars of body + date per delivered article (scraped public content). |
| Translation cache | `history.db` | avoid re-translating | Translated title/body. |
| Run metrics | `history.db` | /metrics | Counts + timings per run; no message content. |

There is **no dedicated user-account store and no message logging**. The
only personal identifier retained is the Telegram `chat_id` inside the
auto-scrape config (needed to deliver scheduled posts).

> Multi-tenant caveat: if the bot is extended to serve multiple users,
> per-user `chat_id`s become the primary key for stored preferences/history
> and this section must be revisited.

## Third parties data is sent to

| Processor | What is sent | When |
|---|---|---|
| Telegram | messages, voice, images, `chat_id` | core function |
| spot.uz | HTTP GETs (no user data) | scraping |
| Microsoft (Edge TTS) | article text to synthesize | when audio requested on Edge engine |
| HuggingFace | model download only | first Supertonic use |
| Groq | article text to translate/summarize | when those features are on |
| Sentry | error traces (PII off; secrets redacted) | if `SENTRY_DSN` set |

Article **text leaves the system** to Edge TTS (Microsoft) and Groq when
those features are used. For a client, disclose this and confirm each
provider's terms permit it.

## Retention & deletion

- Settings/bookmarks: kept until changed/removed (`/unbookmark`, etc.).
- Delivered log: rolling, capped at 5000 most-recent IDs.
- History/translation cache/metrics: kept indefinitely today — **add a
  retention/purge policy before a commercial launch** (e.g. periodic
  delete from `history.db` older than N days).
- Full deletion = delete `history.db` + `user_settings.json`.

## Gaps to close before selling
- Written retention policy + an automated purge job.
- A user-facing "delete my data" path (trivial today since it's two files,
  but should be a documented procedure).
- DPAs / ToS confirmation with Microsoft (Edge TTS), Groq, and Telegram for
  commercial use; content-licensing review for republishing spot.uz.
- If multi-tenant: per-user isolation + consent capture.
