# Tez News Bot

Telegram bot that scrapes Uzbekistan business news from public Telegram channels, fetches full articles, cleans them, filters by your keywords, optionally summarizes with Claude, and delivers as text files or AI-generated audio with Microsoft Edge TTS. Per-user settings, bookmarks, keyword filters, and scrape history are all persisted in SQLite.

## Commands

### Scraping

```
/scrape 50                    Latest 50 articles as .txt file
/scrape 50 audio combined     Latest 50 with one combined MP3
/scrape 50 summary            Prepend a 2-sentence Claude summary to each article
/scrape 35808-35758           Posts by ID (stable, never shifts)
/scrape 2000-1950             Posts by offset from latest
/scrape 50 images             Articles with images
/scrape 50 inline             Send as individual messages
/latest                       Scrape only posts newer than last time

/auto on 3                    Auto-scrape every 3 days
/auto 50 audio combined       Configure auto-scrape options
/auto off                     Disable auto-scrape

/cancel                       Stop a running job
```

### Per-user settings

```
/voice dmitry|andrew|sardor   Switch TTS voice (per-user)
/speed fast                   Change audio speed (slow/normal/fast/faster/fastest)
/speed +30%                   Custom speed value
/lang en|ru|uz                Switch bot language (per-user)
/channel https://t.me/s/...   Switch source channel (per-user)
/status                       Show your current settings
```

### Discovery

```
/filter add <word>            Keep only articles containing the word
/filter exclude <word>        Drop articles containing the word
/filter remove <word>         Remove a rule
/filter list                  Show all rules
/filter clear                 Remove everything

/save <post_id>               Bookmark an article (inline ⭐ Save button too)
/favorites                    List your saved articles
/history                      Last 10 scrape operations with status
```

## Architecture

```
run_bot.py                         Entry point (wires setup_logging + create_app)
spot_bot/
  bot.py                           Command handlers + app factory
  jobs.py                          Background scrape job + auto-scrape scheduler
  pipeline.py                      Orchestrator: scrape → fetch → clean → filter → summary → audio
  config.py                        Constants, timeouts, rate-limits
  settings.py                      Legacy global JSON (migrated once into storage/)
  logging_config.py                Structured logging w/ op_id via contextvars
  errors.py                        UserFacingError + exception classifier
  translations.py                  Localization strings (en/ru/uz)
  handlers/
    features.py                    /latest, /filter, /save, /favorites, /history + ⭐ callback
  scrapers/
    browser_pool.py                Shared Playwright browser (one per process)
    telegram_channel.py            Scroll-and-collect for Telegram channel posts
    article_fetcher.py             Parallel spot.uz article fetch (cache-aware)
  cleaners/
    html_cleaner.py                HTML extraction, block/inline text flow
    text_cleaner.py                Remove ads, URLs, social footers, normalize for TTS
  audio/
    tts_generator.py               Edge TTS, adaptive timeout, parallel batch, combine w/ announcements
  delivery/
    telegram_sender.py             Send text/files/images/audio; RetryAfter-aware
  storage/
    db.py                          aiosqlite connection + migrations
    user_settings.py               Per-user settings w/ legacy JSON migration
    article_cache.py               24h URL cache of parsed articles
    filters.py                     Per-user keyword include/exclude rules
    favorites.py                   Per-user bookmarks
    op_log.py                      Scrape audit trail
  ai/
    summarize.py                   Claude Haiku summaries (optional) + per-lang cache
  utils/
    retry.py                       @async_retry w/ exponential backoff + jitter
```

## Pipeline Flow

```
1. SCRAPE        Shared Playwright browser loads t.me/s/channel, scrolls, extracts posts
                 3 modes: latest N, offset range, post ID range (inclusive)
                 DRY'd into _collect_posts() — single scroll-and-stall loop
                 Output: list of posts with Telegram text + spot.uz links

2. FETCH         For each post with a spot.uz link, fetch full HTML
                 Article cache (24h TTL) checked first — hit skips the browser entirely
                 6 parallel pages (semaphore-limited)
                 Route blocking: CSS/fonts always blocked, images optional
                 @async_retry on navigation; graceful fallback to Telegram text on error
                 Output: articles with title, body, date, images, source

3. CLEAN         Strip ads, navigation, social footers, tracking
                 Block vs inline text extraction (preserves paragraph structure)
                 Remove: URLs, hashtags, cross-references, promo markers
                 Normalize dashes for TTS pacing
                 Runs in asyncio.to_thread so the event loop stays responsive

4. FILTER        Per-user keyword include/exclude (case-insensitive, title+body)
                 Empty-body articles dropped + reported by post ID
                 Output: cleaned, filtered articles

5. SUMMARY       If /scrape ... summary and ANTHROPIC_API_KEY is set:
   (optional)    Claude Haiku 4.5, 2 sentences, cached by (post_id, lang)
                 Adds `summary` field to each article

6. AUDIO         Edge TTS: free Microsoft voices, no API key
   (optional)    4 parallel TTS calls (semaphore-limited)
                 Adaptive timeout (30s base + 10s/1000 chars, capped 180s)
                 Combined mode: generates "Next article: [title]" announcements
                 Binary MP3 concatenation (valid for CBR files)

7. DELIVER       Text: .txt file (default) or inline messages (split at 4096 chars)
                 Audio: individual MP3s or one combined file
                 Images: photos with captions
                 Each article gets an inline ⭐ Save button
                 Telegram RetryAfter handled automatically
```

## Observability

- **Structured logging** — every job gets a short op_id propagated via contextvars, so every scrape/fetch/clean/deliver log line carries it without threading args through call sites.
- **Text + JSON formats** — `LOG_FORMAT=json` for log aggregators; defaults to human-readable.
- **Rotating file logs** — `logs/spot_bot.log` (10 MB × 5 files), plus stderr.
- **Operation audit** — every `/scrape` run is recorded in the `operation_log` table with start/complete/failure/cancel, article count, and error. Viewable via `/history`.

## Reliability

- **Retry with backoff** — `spot_bot.utils.retry.async_retry` (exponential + jitter) on Playwright navigation and TTS.
- **Telegram rate limits** — delivery wraps every send with a RetryAfter-aware loop that honors server-requested sleep exactly.
- **Adaptive TTS timeout** — scales with text length so long articles don't false-timeout.
- **User-safe errors** — `classify_exception()` maps internal errors to translated, actionable messages; raw exception text never leaks to users (full detail goes to logs).

## Performance

Typical timing for 50 articles:

| Phase | Duration | Parallelism |
|---|---|---|
| Scrape channel | 4-8s | 1 shared browser, scroll-based |
| Fetch articles | 15-25s | 6 concurrent pages, shared context |
| Clean text | 1-2s | CPU in worker thread |
| Summary (if on) | 5-15s | 4 concurrent Claude calls, cache hits free |
| Generate audio | 30-50s | 4 concurrent TTS |
| Combine + send | 10-20s | Sequential, rate-limited |
| **Total** | **~65-120s** | |

Caching wins: on repeated ranges, article cache hits cut fetch time by 30-40%. Summary cache is per-(post_id, lang), so regenerating an article in a different UI language still summarizes once per language.

## Hard Limits

| Limit | Value | Why |
|---|---|---|
| Max articles per scrape | 200 | `MAX_SCRAPE_COUNT` |
| Max offset from latest | 5,000 | `MAX_OFFSET` — Telegram pagination |
| Telegram message size | 4,096 chars | Bot API hard limit |
| Telegram file size | 50 MB | Bot API limit |
| Article cache TTL | 24h | Balance freshness vs fetches |
| One active job per chat | enforced | Prevents resource exhaustion |

All timeouts, retry counts, and concurrency levels live in `spot_bot/config.py`.

## Failure Handling

| Failure | What happens |
|---|---|
| spot.uz down / slow | Navigation retried once, then falls back to Telegram text |
| TTS timeout | Skips that article's audio, continues |
| Combined audio >50MB | Falls back to individual MP3 files |
| DB corrupt | Recreates missing tables on startup via migrations |
| Settings JSON corrupt (legacy) | Resets to defaults; DB is source of truth going forward |
| Job already running | Rejects new `/scrape`, suggests `/cancel` |
| Browser crash | Pool reinitializes on next request |
| Cancel during scrape | Stops at next checkpoint; op_log marks 'cancelled' |
| Telegram 429 | RetryAfter honored exactly, then retries |
| Missing ANTHROPIC_API_KEY + /scrape summary | Summary step silently skipped, scrape continues |

## Setup

### Local

```bash
pip install -e .
playwright install chromium

echo "BOT_TOKEN=your_token_here" > .env
# Optional for summaries:
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

python run_bot.py
```

Or with dev extras:

```bash
pip install -e '.[dev,ai]'
pytest                  # 96 tests
ruff check spot_bot     # lint
mypy spot_bot           # type-check
```

### Docker

```bash
docker build -t tez-news-bot .
docker run -e BOT_TOKEN=your_token_here tez-news-bot
```

### Railway (24/7)

1. Push to GitHub
2. Connect repo on railway.app
3. Add `BOT_TOKEN` env var (and optionally `ANTHROPIC_API_KEY`)
4. Auto-deploys on every push

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `BOT_TOKEN` | yes | Telegram bot token from @BotFather |
| `ANTHROPIC_API_KEY` | for /summarize | Enables Claude summaries |
| `ANTHROPIC_MODEL` | no (default claude-haiku-4-5) | Override Claude model id (e.g. `claude-sonnet-4-5`) |
| `LOG_LEVEL` | no (default INFO) | DEBUG / INFO / WARNING / ERROR |
| `LOG_FORMAT` | no (default text) | `text` or `json` |
| `SPOT_LOG_DIR` | no (default ./logs) | Where to write rotating logs |
| `SPOT_DB_PATH` | no | Override SQLite path (default spot_bot.db) |

## Dependencies

| Package | Purpose |
|---|---|
| `playwright` | Headless Chromium for scraping Telegram + spot.uz |
| `beautifulsoup4` + `lxml` | HTML parsing and content extraction |
| `python-telegram-bot[job-queue]` | Bot API + scheduled jobs |
| `edge-tts` | Free Microsoft TTS |
| `aiosqlite` | Async SQLite for per-user state |
| `python-dotenv` | Load env vars from .env |
| `anthropic` (optional) | Claude API for summaries |

## Testing & CI

- **96 tests** cover text + HTML cleaners, date parsing, inclusive-range regression, retry decorator, error classification, storage layer (migrations, per-user isolation, filters, favorites, op-log), AI summarization with mocked Anthropic, and a **full end-to-end pipeline integration test with mocked Playwright** that exercises scrape → fetch → cache → filter → per-user-isolation without touching a real browser.
- **Lint**: `ruff check` clean across `spot_bot` and `tests`.
- **Types**: `mypy` clean; strict mode on storage, pipeline, cleaners, errors, utils, logging.
- **CI**: `.github/workflows/ci.yml` runs lint + type-check + tests on Python 3.11 and 3.12.

## Storage & Data

SQLite at `spot_bot.db` with these tables (see `spot_bot/storage/db.py` for migrations):

```
users              Per-user settings (voice, speed, lang, channel_url, last_scraped_id, auto_scrape_json)
article_cache      URL-keyed parsed articles, 24h TTL
keyword_filters    (user_id, keyword, mode=include|exclude)
favorites          (user_id, post_id, title, body, saved_at)
operation_log      Scrape audit trail (op_id, user_id, status, counts, errors)
summary_cache      (post_id, lang) → AI summary, created lazily if summaries used
```

## Languages and Voices

The bot interface and TTS audio support three languages:

| Language | Bot UI | TTS Voices |
|---|---|---|
| English (`en`) | Full | andrew, ava, emma, brian |
| Russian (`ru`) | Full | dmitry, svetlana |
| Uzbek (`uz`) | Full | madina, sardor |

Switch language: `/lang uz` · Switch voice: `/voice sardor`

Audio announcements in combined MP3 files use the selected language:
- EN: "Next article: [title]"
- RU: "Следующая статья: [title]"
- UZ: "Keyingi maqola: [title]"

## Future Improvements

### Nice to Have
- **Article translation** — auto-translate article body between languages (currently only UI + summaries are localized)
- **Streaming audio delivery** — send articles as TTS finishes instead of waiting for the full batch
- **Web dashboard** — settings UI and favorites browser outside Telegram
- **RSS feed output** — generate per-user RSS from saved articles or scraped content
- **Full-text search** — search scraped article cache and favorites
- **Telegram Stars monetization** — premium features via in-app payments
