"""
Beat strength and drop detection.

Identifies segments with strong beat presence and potential beat drops
(sudden increase in rhythmic energy). Strong, clear beats make for
better ringtone segments.

The output is a score from 0-100 for each time window.
"""

import numpy as np
import librosa

from core.logging import get_logger

log = get_logger()


def compute_beat_profile(audio_path: str,
                         hop_length: int = 512) -> tuple[np.ndarray, list[float], float, int]:
    """
    Compute beat strength over time and find all beat onset times.

    Args:
        audio_path: Path to audio file
        hop_length: Hop length for onset detection

    Returns:
        Tuple of:
            - beat_strength: np.ndarray of onset strength per frame (0-1)
            - beat_times: list of beat onset times in seconds
            - time_per_frame: float
            - sample_rate: int
    """
    log.debug("Computing beat profile for %s", audio_path)

    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # Onset strength envelope (indicates beat strength over time)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    # Normalize to 0-1
    max_val = onset_env.max()
    if max_val > 0:
        onset_env = onset_env / max_val

    # Beat tracking to find beat times
    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
    )
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)

    time_per_frame = hop_length / sr

    return onset_env, list(beat_times), time_per_frame, sr


def compute_drop_score(onset_env: np.ndarray,
                       beat_times: list[float],
                       time_per_frame: float,
                       start: float, end: float) -> float:
    """
    Score a segment for beat drop presence.

    A "drop" is characterized by a sudden increase in onset strength.
    We detect this by looking at the rate of change of onset strength
    around the start of the segment.

    Args:
        onset_env: Onset strength array
        beat_times: List of beat times
        time_per_frame: Seconds per frame
        start: Segment start in seconds
        end: Segment end in seconds

    Returns:
        Drop score 0-100, where 100 is a strong drop at the start.
    """
    start_frame = int(start / time_per_frame)
    end_frame = int(end / time_per_frame)

    start_frame = max(1, min(start_frame, len(onset_env) - 1))
    end_frame = max(start_frame + 1, min(end_frame, len(onset_env)))

    segment = onset_env[start_frame:end_frame]
    if len(segment) < 2:
        return 0.0

    beat_density = sum(1 for bt in beat_times if start <= bt <= end) / (end - start)

    # Onset strength at the very start vs the preceeding frames
    pre_start = max(0, start_frame - int(0.5 / time_per_frame))
    pre_onset = onset_env[pre_start:start_frame]
    post_onset = onset_env[start_frame:start_frame + max(1, int(0.3 / time_per_frame))]

    drop_ratio = 1.0
    if pre_onset.mean() > 0 and len(pre_onset) > 0 and len(post_onset) > 0:
        drop_ratio = post_onset.mean() / max(pre_onset.mean(), 1e-10)

    # If onset strength jumps significantly, it's a drop
    drop_score = min(drop_ratio, 3.0) / 3.0 * 50.0

    # Add beat density score (more beats = more rhythmic = better)
    density_score = min(beat_density * 10, 50.0)

    return drop_score + density_score


def score_segment(audio_path: str, start: float, end: float) -> float:
    """
    Compute a combined beat score (0-100) for a segment.

    Combines: beat strength + beat density + drop presence.

    Args:
        audio_path: Path to audio file
        start: Start time in seconds
        end: End time in seconds

    Returns:
        Score from 0-100.
    """
    onset_env, beat_times, time_per_frame, sr = compute_beat_profile(audio_path)

    # Average onset strength in the segment
    start_frame = int(start / time_per_frame)
    end_frame = int(end / time_per_frame)
    start_frame = max(0, min(start_frame, len(onset_env) - 1))
    end_frame = max(start_frame + 1, min(end_frame, len(onset_env)))

    segment_strength = float(np.mean(onset_env[start_frame:end_frame])) * 30.0

    # Beat density
    density = sum(1 for bt in beat_times if start <= bt <= end) / (end - start)
    density_score = min(density * 15, 30.0)

    # Drop score
    drop_score = compute_drop_score(onset_env, beat_times, time_per_frame, start, end)

    total = segment_strength + density_score + drop_score
    return min(total, 100.0)


def get_beat_times(audio_path: str) -> list[float]:
    """
    Return the list of beat onset times for smart-start snapping.

    Args:
        audio_path: Path to audio file

    Returns:
        List of beat times in seconds.
    """
    _, beat_times, _, _ = compute_beat_profile(audio_path)
    return beat_times
