# Tez News Bot

Telegram bot that scrapes Uzbekistan business news from public Telegram channels, fetches full articles, cleans them, and delivers as text files or AI-generated audio with Microsoft Edge TTS.

## Commands

```
/scrape 50                    Latest 50 articles as .txt file
/scrape 50 audio combined     Latest 50 with one combined MP3
/scrape 35808-35758           Posts by ID (stable, never shifts)
/scrape 2000-1950             Posts by offset from latest
/scrape 50 images             Articles with images
/scrape 50 inline             Send as individual messages

/auto on 3                    Auto-scrape every 3 days
/auto 50 audio combined       Configure auto-scrape options
/auto off                     Disable auto-scrape

/cancel                       Stop a running job
/voice dmitry|andrew|sardor   Switch TTS voice
/speed fast                   Change audio speed (slow/normal/fast/faster/fastest)
/speed +30%                   Custom speed value
/lang en|ru|uz                Switch bot language
/channel https://t.me/s/...   Switch source channel
/status                       Show current settings
```

## Architecture

```
run_bot.py                         Entry point
spot_bot/
  bot.py                           Command handlers + job scheduling
  pipeline.py                      Orchestrator: scrape -> fetch -> clean -> audio
  config.py                        Constants and limits
  settings.py                      Persistent JSON settings (atomic writes)
  translations.py                  Localization strings (en/ru/uz)
  scrapers/
    telegram_channel.py            Playwright scraper for Telegram channels
    article_fetcher.py             Playwright fetcher for spot.uz articles
  cleaners/
    html_cleaner.py                HTML extraction, block/inline text flow
    text_cleaner.py                Remove ads, URLs, social footers, normalize for TTS
  audio/
    tts_generator.py               Edge TTS generation, parallel batch, combine with announcements
  delivery/
    telegram_sender.py             Send text, files, images, audio via Telegram API
```

## Pipeline Flow

```
1. SCRAPE        Playwright loads t.me/s/channel, scrolls, extracts posts
                 3 modes: latest N, offset range, post ID range
                 Output: list of posts with Telegram text + spot.uz links

2. FETCH         For each post with a spot.uz link, fetch full HTML
                 6 parallel Playwright pages (semaphore-limited)
                 Route blocking: CSS/fonts always blocked, images optional
                 Fallback: Telegram text if spot.uz unreachable
                 Output: articles with title, body, date, images

3. CLEAN         Strip ads, navigation, social footers, tracking
                 Block vs inline text extraction (preserves paragraph structure)
                 Remove: URLs, hashtags, cross-references, promo markers
                 Normalize dashes for TTS pacing
                 Output: clean text ready for reading or TTS

4. AUDIO         Edge TTS: free Microsoft voices, no API key
   (optional)    4 parallel TTS calls (semaphore-limited)
                 60-second timeout per article
                 Combined mode: generates "Next article: [title]" announcements
                 Binary MP3 concatenation (valid for CBR files)
                 Output: individual or combined MP3 files

5. DELIVER       Text: .txt file (default) or inline messages (split at 4096 chars)
                 Audio: individual MP3s or one combined file
                 Images: photos with captions
                 Rate-limited: 0.3-0.5s between sends
```

## Hard Limits

| Limit | Value | Why |
|---|---|---|
| Max articles per scrape | 200 | `MAX_SCRAPE_COUNT` — prevents overload |
| Max offset from latest | 5,000 | `MAX_OFFSET` — Telegram pagination limit |
| Telegram message size | 4,096 chars | Telegram Bot API hard limit |
| Telegram file size | 50 MB | Bot API limit — combined audio falls back to individual if exceeded |
| TTS timeout per article | 60 seconds | Prevents hanging on slow Microsoft endpoints |
| Concurrent article fetches | 6 | `MAX_CONCURRENT_FETCHES` — RAM vs speed tradeoff |
| Concurrent TTS calls | 4 | `MAX_CONCURRENT_TTS` — API rate + CPU balance |
| Auto-scrape interval | 1-30 days | Reasonable scheduling bounds |
| One active job per chat | enforced | Prevents resource exhaustion |

## Post ID vs Offset Ranges

**Offsets shift** when new posts are published. `/scrape 2000-1950` points to different posts every day.

**Post IDs are permanent.** Post #35808 is always #35808. The bot auto-detects:
- Numbers <= 5000: treated as offsets from latest
- Numbers > 5000: treated as absolute post IDs

Every scrape shows the post ID range in the summary:
```
Done! Sent 50 articles.
Posts #35808 to #35758.
Next batch: /scrape 35758-35708
```

## Performance

Typical timing for 50 articles:

| Phase | Duration | Parallelism |
|---|---|---|
| Scrape channel | 5-10s | 1 browser, scroll-based |
| Fetch articles | 20-30s | 6 concurrent pages |
| Clean text | 1-2s | CPU-bound |
| Generate audio | 30-50s | 4 concurrent TTS |
| Combine + send | 10-20s | Sequential, rate-limited |
| **Total** | **~70-115s** | |

## Failure Handling

| Failure | What happens |
|---|---|
| spot.uz down | Falls back to Telegram post text |
| TTS timeout (>60s) | Skips that article, continues with rest |
| Combined audio >50MB | Falls back to individual MP3 files |
| Settings file corrupt | Resets to defaults |
| Job already running | Rejects new `/scrape`, suggests `/cancel` |
| Browser crash | Resources cleaned up in `finally` block |
| Cancel during scrape | Stops at next checkpoint, sends partial results |

## Setup

### Local

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure
echo "BOT_TOKEN=your_token_here" > .env

# Run
python run_bot.py
```

### Docker

```bash
docker build -t tez-news-bot .
docker run -e BOT_TOKEN=your_token_here tez-news-bot
```

### Railway (recommended for 24/7)

1. Push to GitHub
2. Connect repo on railway.app
3. Add `BOT_TOKEN` environment variable
4. Auto-deploys on every push

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `BOT_TOKEN` | yes | Telegram bot token from BotFather |
| `SENTRY_DSN` | no | If set, errors are reported to Sentry. Free tier: 5k errors/month at sentry.io |
| `HEARTBEAT_URL` | no | If set, the bot pings this URL every 60 seconds. Use with healthchecks.io / cronitor.io to get an alert when the bot dies. Works from any hosting (no inbound HTTP needed). |

## Dependencies

| Package | Purpose |
|---|---|
| `playwright` | Headless Chromium for scraping Telegram + spot.uz |
| `beautifulsoup4` + `lxml` | HTML parsing and content extraction |
| `python-telegram-bot[job-queue]` | Telegram Bot API + scheduled jobs (APScheduler) |
| `edge-tts` | Free Microsoft TTS — same voices as Edge Read Aloud |
| `python-dotenv` | Load BOT_TOKEN from .env |

## Settings Persistence

Stored in `spot_bot/user_settings.json` with atomic writes (temp file + `os.replace`):

```json
{
  "voice": "ru-RU-DmitryNeural",
  "channel_url": "https://t.me/s/spotuz",
  "speed": "+0%",
  "language": "en",
  "auto_scrape": {
    "enabled": true,
    "interval_days": 3,
    "chat_id": 123456789,
    "count": 50,
    "include_audio": true,
    "combined_audio": true
  }
}
```

## Languages and Voices

The bot interface and TTS audio support three languages:

| Language | Bot UI | TTS Voices |
|---|---|---|
| English (`en`) | Full | andrew, ava, emma, brian |
| Russian (`ru`) | Full | dmitry, svetlana |
| Uzbek (`uz`) | Full | madina, sardor |

Switch language: `/lang uz`
Switch voice: `/voice sardor`

Audio announcements in combined MP3 files use the selected language:
- EN: "Next article: [title]"
- RU: "Следующая статья: [title]"
- UZ: "Keyingi maqola: [title]"

## Future Improvements

### High Value
- **AI summaries** — Claude/GPT to summarize articles, add original value
- **Article translation** — Auto-translate article content between languages
- **Incremental scraping** — Track last-read post ID, only fetch new articles
- **Article caching** — Store fetched articles by URL, avoid re-fetching

### Medium Value
- **Structured logging** — Replace print() with proper logging, add Sentry
- **Health monitoring** — Uptime checks, error rate alerting
- **Multi-user settings** — Per-user preferences instead of global JSON
- **Keyword filtering** — Only deliver articles matching specific topics

### Nice to Have
- **Streaming audio delivery** — Send articles as audio while others still generating
- **Web dashboard** — Settings UI instead of chat commands
- **RSS feed output** — Generate RSS from scraped articles
- **Database storage** — PostgreSQL/SQLite for articles, analytics, search
- **Telegram Stars monetization** — Premium features via in-app payments
