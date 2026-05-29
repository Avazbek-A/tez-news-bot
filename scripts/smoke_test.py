#!/usr/bin/env python3
"""Post-deploy / pre-release smoke test.

Verifies the app wires together without doing anything destructive:
- the Telegram application builds with all handlers,
- the settings layer loads,
- the SQLite layer connects, migrates, and round-trips a metrics row
  (on a throwaway temp DB — never touches the real one).

With --live it also runs the scraper canary (hits the network).

    python -m scripts.smoke_test           # offline build/wiring smoke
    python -m scripts.smoke_test --live    # + live scraper canary

Exits 0 on success, 1 on failure. Suitable as a CI gate or a manual
post-deploy check.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("BOT_TOKEN", "smoke:dummy")


def _check(name, fn):
    try:
        detail = fn()
        print(f"  ✓ {name}: {detail}")
        return True
    except Exception as e:
        print(f"  ✗ {name}: {e!r}")
        return False


def _build_app():
    from spot_bot.bot import create_app
    app = create_app()
    n = sum(len(g) for g in app.handlers.values())
    assert n > 30, f"expected >30 handlers, got {n}"
    return f"{n} handlers registered"


def _load_settings():
    from spot_bot.settings import load_settings
    s = load_settings()
    assert "voice" in s and "skip_seen" in s
    return f"{len(s)} keys"


def _db_roundtrip():
    import spot_bot.history_db as h
    tmp = Path(tempfile.mkdtemp()) / "smoke.db"
    orig = h.DB_PATH
    h.DB_PATH = tmp
    try:
        h.record_run(articles=3, ok=True, duration_ms=100)
        snap = h.metrics_snapshot(days=7)
        assert snap["runs"] == 1 and snap["articles"] == 3, snap
        return "record_run + metrics_snapshot OK"
    finally:
        h.DB_PATH = orig


async def _canary():
    from spot_bot.health import run_canary, format_canary
    report = await run_canary()
    print(format_canary(report))
    if not report["ok"]:
        raise AssertionError("canary failed — see checks above")
    return "live scraper OK"


def main() -> int:
    live = "--live" in sys.argv
    print("Smoke test:")
    ok = True
    ok &= _check("build app", _build_app)
    ok &= _check("load settings", _load_settings)
    ok &= _check("db roundtrip", _db_roundtrip)
    if live:
        ok &= _check("live canary", lambda: asyncio.run(_canary()))
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
