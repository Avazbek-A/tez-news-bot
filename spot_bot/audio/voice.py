"""Helpers for Telegram voice-message delivery.

Telegram only renders audio as a voice message (with mobile speed control,
waveform, and 1x/1.5x/2x playback) when the file is OGG/Opus and sent via
sendVoice. Edge TTS produces MP3, so we convert MP3 -> OGG/Opus with ffmpeg
before sending.

For "combined" audio mode, we also need to split the concatenated stream
into multiple ≤1-hour voice messages, since Telegram caps voice messages
at one hour each.
"""

import asyncio
import os
import shutil
import subprocess
import tempfile

# Telegram caps voice messages at 60 minutes. Leave a small safety margin
# so duration probing rounding errors can't push us over.
VOICE_MAX_DURATION_SECONDS = 58 * 60

# Opus encoding params for Telegram voice messages.
_OPUS_BITRATE = "32k"
_OPUS_SAMPLE_RATE = "24000"


def ffmpeg_available():
    """Return True if ffmpeg + ffprobe are on PATH."""
    return bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe"))


async def _run(cmd, timeout=120):
    """Run a subprocess command asynchronously, returning (rc, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return -1, b"", b"timeout"
    return proc.returncode, stdout, stderr


async def get_audio_duration(path):
    """Return the duration of an audio file in seconds, or 0.0 on failure."""
    if not path or not os.path.exists(path):
        return 0.0
    rc, stdout, _ = await _run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ], timeout=30)
    if rc != 0:
        return 0.0
    try:
        return float(stdout.decode().strip())
    except (ValueError, AttributeError):
        return 0.0


async def convert_mp3_to_opus(mp3_path, ogg_path):
    """Convert an MP3 file to OGG/Opus suitable for Telegram voice messages.

    Returns ogg_path on success, or None on failure.
    """
    if not mp3_path or not os.path.exists(mp3_path):
        return None
    rc, _, stderr = await _run([
        "ffmpeg", "-y",
        "-i", mp3_path,
        "-c:a", "libopus",
        "-b:a", _OPUS_BITRATE,
        "-ar", _OPUS_SAMPLE_RATE,
        "-ac", "1",
        "-application", "voip",
        ogg_path,
    ], timeout=180)
    if rc != 0:
        print(f"ffmpeg convert failed for {mp3_path}: {stderr.decode()[:300]}")
        return None
    if not os.path.exists(ogg_path) or os.path.getsize(ogg_path) == 0:
        return None
    return ogg_path


async def concat_mp3_to_opus(mp3_paths, ogg_path):
    """Concatenate multiple MP3 files into one OGG/Opus file via ffmpeg.

    Uses ffmpeg's concat demuxer (no re-encoding the inputs as a group;
    one Opus encode pass over the concatenated stream).
    """
    if not mp3_paths:
        return None

    # Build a temporary concat list file
    tmp_dir = os.path.dirname(ogg_path) or tempfile.gettempdir()
    list_path = os.path.join(tmp_dir, ".voice_concat_list.txt")
    try:
        with open(list_path, "w", encoding="utf-8") as f:
            for p in mp3_paths:
                escaped = p.replace("'", r"'\''")
                f.write(f"file '{escaped}'\n")

        rc, _, stderr = await _run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c:a", "libopus",
            "-b:a", _OPUS_BITRATE,
            "-ar", _OPUS_SAMPLE_RATE,
            "-ac", "1",
            "-application", "voip",
            ogg_path,
        ], timeout=600)
        if rc != 0:
            print(f"ffmpeg concat-encode failed: {stderr.decode()[:300]}")
            return None
        if not os.path.exists(ogg_path) or os.path.getsize(ogg_path) == 0:
            return None
        return ogg_path
    finally:
        if os.path.exists(list_path):
            try:
                os.remove(list_path)
            except OSError:
                pass


async def split_results_for_voice(results, max_seconds=VOICE_MAX_DURATION_SECONDS):
    """Group (article, mp3_path) tuples into batches whose combined duration
    fits within `max_seconds`. Returns a list of batches; each batch is a
    list of (article, mp3_path) tuples in original order.

    Articles whose individual audio exceeds max_seconds get their own batch
    (Telegram will still cap them; very rare in practice — would be a 60+ min
    interview).
    """
    batches = []
    current = []
    current_dur = 0.0

    for article, path in results:
        if not path or not os.path.exists(path):
            continue
        dur = await get_audio_duration(path)
        if dur <= 0:
            # Unknown duration — assume it might be long, send in own batch
            if current:
                batches.append(current)
                current = []
                current_dur = 0.0
            batches.append([(article, path)])
            continue

        if current and current_dur + dur > max_seconds:
            batches.append(current)
            current = []
            current_dur = 0.0

        current.append((article, path))
        current_dur += dur

    if current:
        batches.append(current)

    return batches


async def compute_chapters(batch):
    """Compute (article, start_seconds) pairs for a single voice-message batch.

    Returns a list of (article, start_seconds) tuples — one per article in
    the batch — where start_seconds is the cumulative offset within the
    voice message at which that article begins.
    """
    chapters = []
    cumulative = 0.0
    for article, path in batch:
        if not path or not os.path.exists(path):
            continue
        chapters.append((article, cumulative))
        dur = await get_audio_duration(path)
        if dur > 0:
            cumulative += dur
    return chapters


def format_timestamp(seconds: float) -> str:
    """Format a duration in seconds as M:SS or H:MM:SS for chapter lists."""
    total = max(0, int(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
