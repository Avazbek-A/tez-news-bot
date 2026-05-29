# Cost model & unit economics

A pre-pricing breakdown of what each part of the bot actually costs to
run, and the third-party terms that constrain commercial use. Numbers are
order-of-magnitude; measure against your own deployment before pricing.

## Fixed / hosting

| Item | Cost | Notes |
|---|---|---|
| Container host (Railway hobby) | ~$5/mo | 1 shared vCPU, ~512 MB–1 GB RAM. One bot instance. |
| Persistent volume | included / small | **Required** — `history.db` + `user_settings.json` must survive redeploys. |
| Supertonic model | $0 | ~99 MB downloaded once at first use; lives in container/volume. |

The architecture is **single-process, single-tenant**. There is no
horizontal scaling today (in-memory `_running_jobs`, local SQLite/JSON).
Each customer = one instance = one host bill.

## Per-use / variable

| Service | Pricing | Commercial caveat |
|---|---|---|
| Telegram Bot API | free | Subject to Telegram ToS + rate limits. |
| Scraping (httpx) | bandwidth only | Subject to spot.uz / Telegram ToS (see RUNBOOK + legal). |
| **Edge TTS** | free | Microsoft's unofficial endpoint; **no SLA, ToS not clearly licensed for commercial resale**. Treat as a risk. |
| **Supertonic TTS** | $0 cash, **CPU time** | ~10–25 s/article on a shared vCPU. The real cost is compute: a 50-article audio scrape can occupy the CPU for 8–20 min. Scaling audio = scaling CPU. |
| Piper TTS | free, local | Offline; CPU cost similar to Supertonic. Opt-in. |
| **Groq** (translation + summaries) | free tier | Rate-limited; **free tier is generally not licensed for commercial/production use** — budget for a paid LLM tier or self-hosted model if these features ship. |
| Image delivery | bandwidth | Images are re-fetched + re-uploaded on the download-fallback path. |
| Sentry / heartbeat | free tiers exist | Optional. |

## Cost drivers to watch

1. **Audio is the expensive feature.** Text-only scrapes are nearly free
   (network + a little CPU). Audio is CPU-bound and serialized for
   Supertonic — it dominates both latency and compute cost. Price audio
   tiers accordingly, or move TTS to a GPU/managed service if volume grows.
2. **LLM features (translate/summarize) need a real budget.** The Groq
   free tier won't carry a paid product. Estimate tokens/article × price
   of whichever provider you license.
3. **Bandwidth** scales with images + audio file sizes, not article count.

## Rough scenario

A single client, text + occasional audio, a few scrapes/day:
- **~$5/mo hosting** dominates; everything else rounds to ~$0 on free tiers.

The moment you (a) enable LLM features for real traffic, (b) serve audio
at volume, or (c) onboard multiple customers, the model changes — that's
when paid LLM, GPU TTS, and a managed datastore enter the budget.
