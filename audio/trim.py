"""
Audio trimming utilities.

Provides functions to cut a segment from an audio file by start/end times
(in seconds). Wraps pydub for the heavy lifting.
"""

from pydub import AudioSegment

from core.logging import get_logger

log = get_logger()


def trim(input_path: str, start: float, end: float, output_path: str | None = None) -> AudioSegment:
    """
    Cut audio from `start` to `end` seconds.

    Args:
        input_path: Path to the audio file (WAV, MP3, etc.)
        start: Start time in seconds
        end: End time in seconds
        output_path: Optional path to save the result

    Returns:
        The trimmed AudioSegment (in memory).
    """
    log.info("Trimming %s from %.2fs to %.2fs", input_path, start, end)
    audio = AudioSegment.from_file(input_path)

    start_ms = int(start * 1000)
    end_ms = int(end * 1000)

    # Clamp to valid range
    start_ms = max(0, min(start_ms, len(audio)))
    end_ms = max(start_ms, min(end_ms, len(audio)))

    trimmed = audio[start_ms:end_ms]

    if output_path:
        log.info("Saving trimmed audio to %s", output_path)
        trimmed.export(output_path, format=_detect_format(output_path))

    return trimmed


def trim_with_smart_start(audio: AudioSegment, target_start: float, target_end: float,
                          beat_times: list[float] | None = None,
                          output_path: str | None = None) -> AudioSegment:
    """
    Same as trim() but snaps start to the nearest detected beat onset
    for a musically cleaner cut.

    Args:
        audio: Already-loaded AudioSegment
        target_start: Desired start time in seconds
        target_end: Desired end time in seconds
        beat_times: List of beat onset times in seconds. If None, uses target_start as-is.
        output_path: Optional path to save the result

    Returns:
        The trimmed AudioSegment.
    """
    start_sec = target_start
    if beat_times:
        # Find the nearest beat onset to our target start
        nearest = min(beat_times, key=lambda b: abs(b - target_start))
        # Only snap if the beat is within 1 second (avoid large jumps)
        if abs(nearest - target_start) < 1.0:
            start_sec = nearest
            log.debug("Snapped start from %.2f to nearest beat at %.2f", target_start, start_sec)

    start_ms = int(start_sec * 1000)
    end_ms = int(target_end * 1000)

    start_ms = max(0, min(start_ms, len(audio)))
    end_ms = max(start_ms, min(end_ms, len(audio)))

    trimmed = audio[start_ms:end_ms]

    if output_path:
        trimmed.export(output_path, format=_detect_format(output_path))

    return trimmed


def _detect_format(path: str) -> str:
    """Guess the audio format from file extension."""
    ext = path.rsplit(".", 1)[-1].lower()
    mapping = {
        "mp3": "mp3",
        "wav": "wav",
        "ogg": "ogg",
        "m4a": "mp4",
        "m4r": "mp4",
        "aac": "adts",
        "flac": "flac",
    }
    return mapping.get(ext, "wav")
