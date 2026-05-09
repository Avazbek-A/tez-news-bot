"""Tests for the Supertonic engine fixes:

- `_load_tts` calls progress_callback with the load milestones.
- `generate_audio_supertonic` enforces a per-call synthesis timeout.
- `generate_batch` uses Semaphore(1) when the active engine is supertonic
  (so CPU-bound ONNX calls don't fight for the GIL).

Tests mock `spot_bot.audio.supertonic_engine` internals so no real model
download or ONNX inference happens.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

import spot_bot.audio.supertonic_engine as se
import spot_bot.audio.tts_generator as tg


@pytest.fixture(autouse=True)
def _reset_supertonic_cache():
    """Each test starts with no cached TTS instance."""
    se._tts_instance = None
    yield
    se._tts_instance = None


class _FakeTTS:
    """Stand-in for the real supertonic.TTS object."""

    def __init__(self, synth_delay: float = 0.0):
        self.synth_delay = synth_delay

    def get_voice_style(self, voice_name="M1"):
        return object()

    def synthesize(self, text, voice_style=None, lang="en"):
        if self.synth_delay:
            import time
            time.sleep(self.synth_delay)
        return (b"\x00\x00", 0.1)

    def save_audio(self, wav, path):
        with open(path, "wb") as f:
            f.write(b"\x00\x00")


# ---------- Fix 1: progress_callback fires with model-load milestones ----------

@pytest.mark.asyncio
async def test_load_tts_emits_progress_callbacks(monkeypatch):
    messages = []

    async def cb(msg):
        messages.append(msg)

    async def fake_to_thread(fn, *args, **kwargs):
        return _FakeTTS()

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    result = await se._load_tts(progress_callback=cb)
    assert result is not None
    assert len(messages) == 2
    assert "Loading Supertonic" in messages[0]
    assert "loaded" in messages[1].lower()


@pytest.mark.asyncio
async def test_load_tts_skips_callback_when_cached(monkeypatch):
    """Once loaded, subsequent calls don't re-emit the load milestones."""
    se._tts_instance = _FakeTTS()
    messages = []

    async def cb(msg):
        messages.append(msg)

    result = await se._load_tts(progress_callback=cb)
    assert result is not None
    assert messages == []


@pytest.mark.asyncio
async def test_load_tts_progress_callback_optional(monkeypatch):
    """No callback → no error."""
    async def fake_to_thread(fn, *args, **kwargs):
        return _FakeTTS()

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    result = await se._load_tts()  # no callback
    assert result is not None


# ---------- Fix 3: per-call synthesis timeout ----------

@pytest.mark.asyncio
async def test_generate_audio_supertonic_times_out(monkeypatch, tmp_path):
    """A synth call that exceeds the timeout returns None instead of hanging."""
    se._tts_instance = _FakeTTS()

    # Patch the timeout to something fast for the test
    monkeypatch.setattr(se, "_SYNTH_TIMEOUT_SECONDS", 0.05)

    async def slow_synth():
        await asyncio.sleep(1.0)
        return b"\x00"

    real_to_thread = asyncio.to_thread

    async def fake_to_thread(fn, *args, **kwargs):
        # Make the synth thread "hang"; everything else passes through.
        if fn.__name__ == "_do_synth":
            return await slow_synth()
        return await real_to_thread(fn, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    out = tmp_path / "out.mp3"
    result = await se.generate_audio_supertonic(
        "hello world", str(out), lang="en",
    )
    assert result is None


# ---------- Fix 2: Semaphore(1) for supertonic in generate_batch ----------

@pytest.mark.asyncio
async def test_generate_batch_uses_serial_semaphore_for_supertonic(monkeypatch):
    """When voice_engine=supertonic, generate_batch must serialize calls
    so CPU-bound ONNX inference doesn't fight for the GIL."""
    from spot_bot import settings as settings_mod

    # Force the active engine to supertonic
    monkeypatch.setattr(
        settings_mod, "get_setting",
        lambda key: "supertonic" if key == "voice_engine" else None,
    )

    # Track concurrency: how many generate_audio calls are in flight at once
    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    async def fake_generate_audio(text, output_path, voice, rate,
                                  cancel_event=None, progress_callback=None):
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        await asyncio.sleep(0.02)
        async with lock:
            in_flight -= 1
        # Write a non-empty stub so caller treats it as success
        with open(output_path, "wb") as f:
            f.write(b"\x00")
        return output_path

    monkeypatch.setattr(tg, "generate_audio", fake_generate_audio)

    articles = [
        {"title": f"a{i}", "body": "x" * 50} for i in range(4)
    ]
    results = await tg.generate_batch(articles)
    assert len(results) == 4
    assert peak == 1, f"Expected serial execution, saw peak concurrency={peak}"


@pytest.mark.asyncio
async def test_generate_batch_uses_parallel_semaphore_for_edge(monkeypatch):
    """For Edge engine, the existing MAX_CONCURRENT_TTS parallelism is preserved."""
    from spot_bot import settings as settings_mod

    monkeypatch.setattr(
        settings_mod, "get_setting",
        lambda key: "edge" if key == "voice_engine" else None,
    )

    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    async def fake_generate_audio(text, output_path, voice, rate,
                                  cancel_event=None, progress_callback=None):
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1
        with open(output_path, "wb") as f:
            f.write(b"\x00")
        return output_path

    monkeypatch.setattr(tg, "generate_audio", fake_generate_audio)

    articles = [
        {"title": f"a{i}", "body": "x" * 50} for i in range(4)
    ]
    results = await tg.generate_batch(articles)
    assert len(results) == 4
    # Edge should run multiple in parallel (MAX_CONCURRENT_TTS defaults to >=2)
    assert peak >= 2, f"Edge should run in parallel, saw peak={peak}"
