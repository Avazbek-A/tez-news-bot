# Operations runbook

How to deploy, monitor, back up, and recover the bot. Aimed at whoever is
on call for a client deployment.

## Environment variables

| Var | Required | Purpose |
|---|---|---|
| `BOT_TOKEN` | **yes** | Telegram bot token. |
| `GROQ_API_KEY` | no | Enables /translate + /summarize. Without it those degrade gracefully. |
| `GROQ_MODEL` | no | Override the default Llama model. |
| `ALERT_CHAT_ID` | recommended | Telegram chat that receives 🚨 operational alerts (scraper breakage, high error rate). |
| `SENTRY_DSN` | recommended | Error tracking. |
| `HEARTBEAT_URL` | recommended | Uptime ping (healthchecks.io / cronitor). |
| `LOG_LEVEL` / `LOG_FORMAT` | no | `INFO` default; `LOG_FORMAT=json` for structured logs. |
| `PIPER_VOICE_DIR` | no | Local Piper models, if used. |

Secrets are redacted from logs automatically (see `logging_setup.RedactingFilter`).

## Persistent state — DO NOT lose this

All durable state lives in two files **inside the app directory**:
- `spot_bot/history.db` — delivery history, bookmarks, translation cache, metrics.
- `spot_bot/user_settings.json` — all user preferences + auto-scrape config.

**These must be on a persistent volume.** On Railway/containers the
default filesystem is ephemeral — a redeploy wipes them. Mount a volume
and ensure both paths are on it.

### Backups
- Back up `history.db` and `user_settings.json` on a schedule (e.g. daily
  copy to object storage). `history.db` is SQLite — copy while idle or use
  `sqlite3 history.db ".backup"`.
- **Restore**: stop the bot, drop both files back in place, start.

### Schema migrations
- `history.db` is versioned via `PRAGMA user_version`; new migrations go
  in `history_db._MIGRATIONS` and apply automatically on next connect.
- `user_settings.json` is versioned via `settings_version`; migrations go
  in `settings._migrate_settings`.
- Both are forward-only and idempotent. Take a backup before deploying a
  release that bumps either version.

## Monitoring

- **`/metrics`** (in-bot): 7-day health — runs, articles, error %, partial
  %, avg run time. First place to look.
- **Scraper canary** (`.github/workflows/canary.yml`, or `python -m
  scripts.healthcheck`): runs twice daily against the live site; fails +
  notifies if Telegram/spot.uz markup changed and our selectors broke.
- **Alerts**: the bot auto-alerts (ERROR log → Sentry, + Telegram to
  `ALERT_CHAT_ID`) on zero-yield scrapes and sustained error rates.
- **Heartbeat**: external uptime check via `HEARTBEAT_URL`.

## Common incidents

### "Scrapes return 0 articles"
Almost always a markup change. 1) Run `python -m scripts.healthcheck` to
pinpoint which check broke (channel parse vs. article body vs. images).
2) Inspect the live HTML for the changed selector. 3) Update the relevant
selector: channel post fields in `scrapers/telegram_channel.py`, article
body/images in `config.BODY_SELECTORS` + `cleaners/html_cleaner.py`.
4) Add/refresh a fixture in `tests/fixtures/` and a test so it can't
silently regress again.

### "Audio is very slow / times out"
Expected for Supertonic on shared CPU (serialized, ~10–25 s/article; 90–300 s
hard timeout per call). For volume, switch `/voice_engine edge` or move TTS
to a GPU/managed service. See COSTS.md.

### "LLM features stopped working"
Check `GROQ_API_KEY` and Groq rate limits/quota. Features degrade to
untranslated/unsummarized rather than failing the scrape.

## Deploy & rollback
- CI (`.github/workflows/ci.yml`) runs ruff + mypy + the full test suite
  on every push/PR; keep `main` green.
- Roll back by redeploying the previous commit. State files are
  backward-compatible within a schema version; if a deploy bumped a
  version, restore the pre-deploy DB/settings backup.

## Secret rotation
- Rotate `BOT_TOKEN` via BotFather, update the env var, redeploy. Old
  token stops working immediately.
- Rotate `GROQ_API_KEY` / `SENTRY_DSN` in the provider console + env.
- Logs never contain these values (redaction filter), but rotate anyway if
  a host or backup was exposed.
