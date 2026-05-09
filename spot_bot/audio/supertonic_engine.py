"""Supertonic-3 TTS engine (ONNX-based, CPU-friendly, ~99M params).

Supertonic supports 31 languages including English and Russian — perfect
for our RU/EN articles. Uzbek is NOT in its language list, so the
voice-engine router falls back to Edge TTS for Uzbek.

License: model is OpenRAIL-M; code samples are MIT. Compatible with our
deployment.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# Lazily-loaded TTS instance (one per process). Loading takes ~1-2s and
# pulls the ~99 MB model from HF on first run.
_tts_instance = None
_tts_load_lock = asyncio.Lock()


# ISO 639-1 codes Supertonic accepts. Keep this conservative to what we
# actually need; Supertonic supports 31 langs total.
_SUPPORTED_LANGS = {
    "en": "en",
    "ru": "ru",
    "de": "de",
    "tr": "tr",
}


def supertonic_supports(lang: str) -> bool:
    """Return True if Supertonic can synthesize for this language code."""
    return (lang or "").lower() in _SUPPORTED_LANGS


async def _load_tts():
    """Load the Supertonic TTS instance, caching across calls."""
    global _tts_instance
    if _tts_instance is not None:
        return _tts_instance
    async with _tts_load_lock:
        if _tts_instance is not None:
            return _tts_instance

        def _do_load():
            from supertonic import TTS
            return TTS(auto_download=True)

        try:
            _tts_instance = await asyncio.to_thread(_do_load)
            logger.info("[supertonic] model loaded")
        except Exception as e:
            logger.warning("[supertonic] failed to load: %s", e)
            _tts_instance = None
        return _tts_instance


def _parse_speed_to_atempo(rate: str) -> Optional[float]:
    """Map Edge-style '+25%' / '-20%' to ffmpeg atempo factor (1+rate/100).
    Returns None if no speed change is needed."""
    try:
        s = (rate or "+0%").strip().rstrip("%")
        n = float(s)
    except ValueError:
        return None
    if abs(n) < 1:
        return None
    factor = 1.0 + n / 100.0
    # ffmpeg atempo accepts 0.5 .. 2.0
    return max(0.5, min(2.0, factor))


async def _wav_to_mp3(wav_path: str, mp3_path: str,
                     atempo: Optional[float] = None) -> bool:
    """Convert WAV to MP3 via ffmpeg, optionally adjusting playback speed.
    Returns True on success."""
    cmd = ["ffmpeg", "-y", "-i", wav_path]
    if atempo is not None:
        cmd += ["-filter:a", f"atempo={atempo:.3f}"]
    cmd += ["-codec:a", "libmp3lame", "-b:a", "48k", mp3_path]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=180)
    except asyncio.TimeoutError:
        proc.kill()
        return False
    return os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0


async def generate_audio_supertonic(text: str, output_path: str,
                                    lang: str = "en",
                                    speed_rate: str = "+0%") -> Optional[str]:
    """Synthesize `text` to MP3 at `output_path` via Supertonic.
    Returns output_path on success, or None on any failure (so the
    caller can fall back to Edge TTS).
    """
    if not text or not text.strip():
        return None
    if not supertonic_supports(lang):
        return None

    tts = await _load_tts()
    if tts is None:
        return None

    voice_name = "M1"  # default voice; Supertonic ships several

    def _do_synth():
        style = tts.get_voice_style(voice_name=voice_name)
        wav, _duration = tts.synthesize(
            text, voice_style=style, lang=_SUPPORTED_LANGS[lang],
        )
        return wav

    try:
        wav = await asyncio.to_thread(_do_synth)
    except Exception as e:
        logger.warning("[supertonic] synthesis failed: %s", e)
        return None

    wav_path = output_path + ".wav"
    try:
        def _save():
            tts.save_audio(wav, wav_path)
        await asyncio.to_thread(_save)
    except Exception as e:
        logger.warning("[supertonic] save failed: %s", e)
        return None

    atempo = _parse_speed_to_atempo(speed_rate)
    ok = await _wav_to_mp3(wav_path, output_path, atempo=atempo)
    if os.path.exists(wav_path):
        try:
            os.remove(wav_path)
        except OSError:
            pass

    if not ok:
        return None
    return output_path
