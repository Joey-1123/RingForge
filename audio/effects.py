"""
Audio effects for ringtone optimization.

Provides normalize, fade in/out, bass boost, silence removal, and a
convenience function that applies the full ringtone treatment.
"""

from pydub import AudioSegment
from pydub.effects import normalize as pydub_normalize

from core.logging import get_logger

log = get_logger()


def apply_fade(audio: AudioSegment, fade_ms: int = 200) -> AudioSegment:
    """
    Apply a fade-in and fade-out to the audio segment.

    Args:
        audio: Input AudioSegment
        fade_ms: Duration of the fade in milliseconds (default 200)

    Returns:
        AudioSegment with fades applied.
    """
    if fade_ms <= 0:
        return audio
    return audio.fade_in(fade_ms).fade_out(fade_ms)


def normalize(audio: AudioSegment, target_dbfs: float = -1.0) -> AudioSegment:
    """
    Normalize the audio to a target peak loudness.

    Args:
        audio: Input AudioSegment
        target_dbfs: Target peak loudness in dBFS (default -1.0)

    Returns:
        Normalized AudioSegment.
    """
    log.debug("Normalizing to %.1f dBFS", target_dbfs)
    normalized = pydub_normalize(audio)
    # Adjust to exact target dBFS
    change = target_dbfs - normalized.max_dBFS
    return normalized.apply_gain(change)


def bass_boost(audio: AudioSegment, gain: float = 4.0) -> AudioSegment:
    """
    Boost the low frequencies (bass) by applying a low-shelf filter.

    Args:
        audio: Input AudioSegment
        gain: Amount of boost in dB (default 4.0)

    Returns:
        AudioSegment with boosted bass.
    """
    log.debug("Applying bass boost: +%.1f dB", gain)
    # pydub's low_pass_filter is for cutting, not boosting.
    # We use a simple approach: mix in a low-passed copy.
    low_pass = audio.low_pass_filter(200)
    boosted = audio.overlay(low_pass.apply_gain(gain))
    return boosted


def remove_silence(audio: AudioSegment,
                   silence_thresh: int = -40,
                   min_silence_len: int = 500) -> AudioSegment:
    """
    Remove leading and trailing silence from an audio segment.

    Args:
        audio: Input AudioSegment
        silence_thresh: Silence threshold in dBFS (default -40)
        min_silence_len: Minimum silence length in ms (default 500)

    Returns:
        AudioSegment with silence trimmed from both ends.
    """
    log.debug("Removing silence (threshold=%d dBFS, min_len=%d ms)",
              silence_thresh, min_silence_len)

    # Strip silence from both ends using pydub's detect_silence
    from pydub.silence import detect_leading_silence

    start_trim = detect_leading_silence(audio, silence_threshold=silence_thresh,
                                        chunk_size=10)
    end_trim = detect_leading_silence(audio.reverse(), silence_threshold=silence_thresh,
                                      chunk_size=10)

    duration_ms = len(audio)
    trimmed = audio[start_trim:duration_ms - end_trim]

    # Only trim if we remove at least min_silence_len
    if len(audio) - len(trimmed) >= min_silence_len:
        return trimmed

    return audio


def apply_all(audio: AudioSegment,
              do_normalize: bool = True,
              do_fade: bool = True,
              do_bass: bool = False,
              do_silence: bool = False,
              normalize_db: float = -1.0,
              fade_ms: int = 200,
              bass_gain: float = 4.0) -> AudioSegment:
    """
    Apply a chain of common ringtone effects.

    Order: silence removal -> normalize -> fade -> bass boost

    Args:
        audio: Input AudioSegment
        do_normalize: Apply normalization
        do_fade: Apply fade in/out
        do_bass: Apply bass boost
        do_silence: Remove leading/trailing silence
        normalize_db: Target peak loudness
        fade_ms: Fade duration in ms
        bass_gain: Bass boost gain in dB

    Returns:
        Processed AudioSegment.
    """
    if do_silence:
        audio = remove_silence(audio)

    if do_normalize:
        audio = normalize(audio, target_dbfs=normalize_db)

    if do_fade:
        audio = apply_fade(audio, fade_ms=fade_ms)

    if do_bass:
        audio = bass_boost(audio, gain=bass_gain)

    return audio
