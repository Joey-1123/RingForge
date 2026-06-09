"""
Audio metadata extraction beyond basic YouTube metadata.

Uses librosa to extract musical features like tempo (BPM), key,
and loudness from the downloaded audio file.
"""

import librosa

from core.logging import get_logger

log = get_logger()


def analyze_audio(audio_path: str) -> dict:
    """
    Extract musical features from an audio file.

    Args:
        audio_path: Path to audio file (WAV, MP3, etc.)

    Returns:
        Dict with keys:
            - duration: float (seconds)
            - sample_rate: int
            - channels: int
            - tempo: float (BPM) or None
            - key: str (e.g. 'C major') or None
            - loudness: float (dB) or None
    """
    log.info("Analyzing audio: %s", audio_path)

    # Load audio
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    metadata = {
        "duration": duration,
        "sample_rate": int(sr),
        "channels": 1,  # librosa loads as mono by default
        "tempo": None,
        "key": None,
        "loudness": None,
    }

    # Estimate tempo (BPM) via beat tracking
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        metadata["tempo"] = float(tempo[0]) if hasattr(tempo, '__getitem__') else float(tempo)
    except Exception as e:
        log.debug("Tempo estimation failed: %s", e)

    # Estimate key (using Krumhansl-Schmuckler algorithm via librosa)
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key = _estimate_key(chroma)
        metadata["key"] = key
    except Exception as e:
        log.debug("Key estimation failed: %s", e)

    # Compute integrated loudness (approximate RMS in dB)
    try:
        rms = librosa.feature.rms(y=y)
        metadata["loudness"] = float(20 * librosa.amplitude_to_db(rms, ref=1.0).mean())
    except Exception as e:
        log.debug("Loudness estimation failed: %s", e)

    return metadata


# Mapping of pitch class profiles for key detection
# (Krumhansl-Schmuckler key profiles)
_MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                   2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                   2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

_PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F",
                "F#", "G", "G#", "A", "A#", "B"]


def _estimate_key(chroma: librosa.feature.Chroma) -> str:
    """
    Estimate the musical key from a chromagram.

    Uses correlation with Krumhansl-Schmuckler profiles.
    """
    chroma_mean = chroma.mean(axis=1)

    # Correlate with major and minor profiles
    corr_major = _correlation(chroma_mean, _MAJOR_PROFILE)
    corr_minor = _correlation(chroma_mean, _MINOR_PROFILE)

    major_idx = int(corr_major.argmax())
    minor_idx = int(corr_minor.argmax())

    if corr_major[major_idx] >= corr_minor[minor_idx]:
        return f"{_PITCH_NAMES[major_idx]} major"
    else:
        return f"{_PITCH_NAMES[minor_idx]} minor"


def _correlation(a, b):
    """Compute correlation between array a and profile b, cyclically shifted."""
    import numpy as np
    a = np.asarray(a)
    b = np.asarray(b)
    corrs = []
    for shift in range(12):
        rolled = np.roll(a, shift)
        corr = np.corrcoef(rolled, b)[0, 1]
        corrs.append(corr)
    return np.array(corrs)
