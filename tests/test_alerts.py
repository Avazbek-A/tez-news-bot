"""Tests for operational alerting (zero-yield + error-rate)."""
from __future__ import annotations

import types

import pytest

import spot_bot.alerts as alerts


def _result(articles=0, skipped=0, muted=0, partial=False):
    return types.SimpleNamespace(
        articles=[{}] * articles,
        skipped_seen_count=skipped,
        muted_count=muted,
        partial=partial,
    )


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Capture alerts instead of sending; reset cooldown; stub metrics."""
    sent = []

    async def fake_send(bot, text):
        sent.append(text)

    monkeypatch.setattr(alerts, "send_alert", fake_send)
    monkeypatch.setattr(alerts, "_last_alert_at", {})
    # Default: clean metrics so the error-rate trigger stays silent unless
    # a test overrides it.
    monkeypatch.setattr(
        alerts.history_db, "metrics_snapshot",
        lambda days=1: {"runs": 0, "errors": 0},
    )
    return sent


@pytest.mark.asyncio
async def test_zero_yield_triggers_alert(_reset):
    await alerts.evaluate_scrape_health(
        None, result=_result(articles=0), run_ok=True,
        latest_mode=True, requested_count=10,
    )
    assert len(_reset) == 1
    assert "Zero-yield" in _reset[0]


@pytest.mark.asyncio
async def test_articles_delivered_no_alert(_reset):
    await alerts.evaluate_scrape_health(
        None, result=_result(articles=5), run_ok=True,
        latest_mode=True, requested_count=10,
    )
    assert _reset == []


@pytest.mark.asyncio
async def test_skipped_seen_explains_empty_no_alert(_reset):
    await alerts.evaluate_scrape_health(
        None, result=_result(articles=0, skipped=10), run_ok=True,
        latest_mode=True, requested_count=10,
    )
    assert _reset == []


@pytest.mark.asyncio
async def test_muted_explains_empty_no_alert(_reset):
    await alerts.evaluate_scrape_health(
        None, result=_result(articles=0, muted=10), run_ok=True,
        latest_mode=True, requested_count=10,
    )
    assert _reset == []


@pytest.mark.asyncio
async def test_partial_explains_empty_no_alert(_reset):
    await alerts.evaluate_scrape_health(
        None, result=_result(articles=0, partial=True), run_ok=True,
        latest_mode=True, requested_count=10,
    )
    assert _reset == []


@pytest.mark.asyncio
async def test_explicit_range_empty_no_alert(_reset):
    """An explicit range/post-id/title scrape returning 0 is a legitimate
    answer, not breakage — don't alert."""
    await alerts.evaluate_scrape_health(
        None, result=_result(articles=0), run_ok=True,
        latest_mode=False, requested_count=10,
    )
    assert _reset == []


@pytest.mark.asyncio
async def test_zero_yield_cooldown(_reset):
    """Second identical zero-yield within the cooldown doesn't re-alert."""
    for _ in range(2):
        await alerts.evaluate_scrape_health(
            None, result=_result(articles=0), run_ok=True,
            latest_mode=True, requested_count=10,
        )
    assert len(_reset) == 1  # cooldown suppressed the second


@pytest.mark.asyncio
async def test_high_error_rate_triggers_alert(_reset, monkeypatch):
    monkeypatch.setattr(
        alerts.history_db, "metrics_snapshot",
        lambda days=1: {"runs": 4, "errors": 3},  # 75%
    )
    # Deliver articles so the zero-yield path stays silent; only error-rate fires.
    await alerts.evaluate_scrape_health(
        None, result=_result(articles=2), run_ok=True,
        latest_mode=True, requested_count=10,
    )
    assert len(_reset) == 1
    assert "error rate" in _reset[0]


@pytest.mark.asyncio
async def test_low_error_rate_no_alert(_reset, monkeypatch):
    monkeypatch.setattr(
        alerts.history_db, "metrics_snapshot",
        lambda days=1: {"runs": 10, "errors": 1},  # 10%
    )
    await alerts.evaluate_scrape_health(
        None, result=_result(articles=2), run_ok=True,
        latest_mode=True, requested_count=10,
    )
    assert _reset == []
