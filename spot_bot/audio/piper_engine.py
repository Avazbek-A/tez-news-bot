"""Optional Piper TTS backend (Apache-2.0, fully open-source, runs locally on CPU).

Edge TTS is the default engine; this module is opt-in via /voice_engine
piper. We don't pre-install Piper in the default Dockerfile to keep the
image small (Piper + its onnxruntime dependency + voice models add
~200-300MB). To enable Piper:

    1. Add `piper-tts` to requirements.txt.
    2. Drop voice .onnx + .onnx.json model files into /app/piper-models/
       (download from https://github.com/rhasspy/piper/releases).
    3. Set PIPER_VOICE_DIR env var if you put them elsewhere.
    4. /voice_engine piper

The bot falls back to Edge TTS gracefully if any of the above is missing.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_VOICE_DIR_ENV = "PIPER_VOICE_DIR"
_DEFAULT_VOICE_DIR = "/app/piper-models"

# Cached PiperVoice instances per language code so we don't re-load the
# 30-60MB ONNX model on every TTS call.
_voice_cache: dict[str, object] = {}


def _voice_dir() -> Path:
    return Path(os.environ.get(_VOICE_DIR_ENV) or _DEFAULT_VOICE_DIR)


def piper_available() -> bool:
    """True if the piper-tts package is importable AND at least one voice
    model file exists in the configured directory."""
    try:
        import piper  # noqa: F401
    except ImportError:
        return False
    d = _voice_dir()
    if not d.is_dir():
        return False
    return any(p.suffix == ".onnx" for p in d.iterdir())


def _resolve_voice_for_lang(lang: str) -> Optional[Path]:
    """Pick a voice .onnx file for the given language code (en/ru/uz).

    Looks for a filename containing the lang code (case-insensitive). If
    nothing matches, falls back to any available .onnx file.
    """
    d = _voice_dir()
    if not d.is_dir():
        return None
    candidates = sorted(p for p in d.iterdir() if p.suffix == ".onnx")
    if not candidates:
        return None
    lang = (lang or "en").lower()
    # Prefer filenames containing the lang code (e.g. ru_RU-irina-medium.onnx)
    for p in candidates:
        if lang in p.name.lower():
            return p
    return candidates[0]


def _load_voice(model_path: Path):
    if str(model_path) in _voice_cache:
        return _voice_cache[str(model_path)]
    try:
        from piper import PiperVoice
    except ImportError as e:
        raise RuntimeError(f"piper-tts not installed: {e}")
    config_path = model_path.with_suffix(model_path.suffix + ".json")
    voice = PiperVoice.load(str(model_path), config_path=str(config_path))
    _voice_cache[str(model_path)] = voice
    return voice


def _synthesize_sync(text: str, output_wav: str, model_path: Path,
                     length_scale: float = 1.0):
    """Synthesize `text` into a WAV file at `output_wav`. Synchronous —
    callers should run this in a thread pool via asyncio.to_thread."""
    import wave
    voice = _load_voice(model_path)
    with wave.open(output_wav, "wb") as wav_file:
        voice.synthesize(text, wav_file, length_scale=length_scale)


async def generate_audio_piper(text: str, output_path: str, lang: str = "en",
                               speed_rate: str = "+0%") -> Optional[str]:
    """Generate audio via Piper, returning output_path on success or None.

    speed_rate uses Edge TTS's "+30%"/"-20%" convention; we map it to
    Piper's length_scale (1.0 default; >1 slows down, <1 speeds up).
    """
    if not text or not text.strip():
        return None
    model_path = _resolve_voice_for_lang(lang)
    if model_path is None:
        logger.warning("[piper] no voice model found in %s", _voice_dir())
        return None

    # Map "+25%" → length_scale ~ 0.8 (faster), "-20%" → ~1.25 (slower)
    length_scale = 1.0
    try:
        rate_str = (speed_rate or "+0%").strip().rstrip("%")
        rate_num = float(rate_str)
        # +25% means 1.25x speed → length_scale = 1/1.25 = 0.8
        length_scale = 1.0 / (1.0 + rate_num / 100.0)
        length_scale = max(0.5, min(2.0, length_scale))
    except (ValueError, ZeroDivisionError):
        length_scale = 1.0

    # Piper writes WAV; we'll convert to MP3 via ffmpeg so the rest of the
    # pipeline (which expects MP3 and binary-concats them) keeps working.
    wav_path = output_path + ".wav"
    try:
        await asyncio.to_thread(
            _synthesize_sync, text, wav_path, model_path, length_scale,
        )
    except Exception as e:
        logger.warning("[piper] synthesis failed: %s", e)
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass
        return None

    # WAV → MP3 via ffmpeg (already in the container for voice messages)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-b:a", "48k",
        output_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=180)
    except asyncio.TimeoutError:
        proc.kill()
        try:
            os.remove(wav_path)
        except OSError:
            pass
        return None
    finally:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return None
    return output_path
