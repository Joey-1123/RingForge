"""
Energy-based scoring for audio segments.

Computes the RMS energy envelope of the audio and scores candidate segments
by their average energy. High-energy sections (loud, intense) tend to make
better ringtones.

The output is a score from 0-100 for each time window, where 100 is the
highest-energy window in the audio.
"""

import numpy as np
import librosa

from core.logging import get_logger

log = get_logger()


def compute_energy_profile(audio_path: str,
                           hop_length: int = 512) -> tuple[np.ndarray, float, int]:
    """
    Load audio and compute the RMS energy envelope.

    Args:
        audio_path: Path to audio file
        hop_length: Hop length for STFT analysis (smaller = higher time resolution)

    Returns:
        Tuple of (energy_array, sampling_interval_seconds, sample_rate)
    """
    log.debug("Computing energy profile for %s", audio_path)

    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # Compute RMS energy
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    # Time per frame
    time_per_frame = hop_length / sr

    return rms, time_per_frame, sr


def score_windows(audio_path: str,
                  window_duration: float = 30.0,
                  hop_duration: float = 1.0) -> list[dict]:
    """
    Score overlapping windows of the audio by average energy.

    Returns a list of dicts sorted by score descending, each with:
        - start: float (seconds)
        - end: float (seconds)
        - score: float (0-100)

    Args:
        audio_path: Path to audio file
        window_duration: Length of each candidate window in seconds
        hop_duration: Step between consecutive windows in seconds
    """
    rms, time_per_frame, sr = compute_energy_profile(audio_path)
    total_duration = len(rms) * time_per_frame

    window_frames = int(window_duration / time_per_frame)
    hop_frames = int(hop_duration / time_per_frame)

    if window_frames >= len(rms):
        # Audio is shorter than window; score the whole thing
        avg_energy = float(np.mean(rms))
        return [{
            "start": 0.0,
            "end": total_duration,
            "score": 100.0,  # only one window, it's the best by default
        }]

    windows = []
    for start_frame in range(0, len(rms) - window_frames + 1, hop_frames):
        end_frame = start_frame + window_frames
        window_rms = rms[start_frame:end_frame]
        avg_energy = float(np.mean(window_rms))
        start_time = start_frame * time_per_frame
        end_time = end_frame * time_per_frame

        windows.append({
            "start": start_time,
            "end": end_time,
            "score": avg_energy,
        })

    if not windows:
        return []

    # Normalize scores to 0-100
    max_energy = max(w["score"] for w in windows)
    min_energy = min(w["score"] for w in windows)
    energy_range = max_energy - min_energy

    if energy_range < 1e-10:
        # All windows have the same energy; assign 50 to all
        for w in windows:
            w["score"] = 50.0
    else:
        for w in windows:
            w["score"] = (w["score"] - min_energy) / energy_range * 100.0

    # Sort by score descending
    windows.sort(key=lambda w: w["score"], reverse=True)
    return windows


def score_segment(audio_path: str, start: float, end: float) -> float:
    """
    Compute a 0-100 energy score for a specific segment of audio.

    Args:
        audio_path: Path to audio file
        start: Start time in seconds
        end: End time in seconds

    Returns:
        Energy score from 0-100, where 100 is the highest-energy segment.
    """
    all_windows = score_windows(audio_path, window_duration=end - start)
    if not all_windows:
        return 0.0

    # Find the window closest to our target segment
    target_mid = (start + end) / 2
    closest = min(all_windows, key=lambda w: abs((w["start"] + w["end"]) / 2 - target_mid))

    return closest["score"]
