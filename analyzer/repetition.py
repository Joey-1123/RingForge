"""
Repetition/chorus detection using librosa.

Identifies sections of the audio that repeat (choruses, hooks) by computing
a self-similarity matrix and finding diagonal stripes that indicate repetition.

The output is a score from 0-100 for each time window, where 100 is the most
repetition-rich segment (likely a chorus).
"""

import numpy as np
import librosa

from core.logging import get_logger

log = get_logger()


def compute_repetition_profile(audio_path: str,
                               hop_length: int = 512) -> tuple[np.ndarray, float, int]:
    """
    Compute a repetition salience profile over time.

    Uses beat-synchronous chroma features and a self-similarity matrix to find
    regions with strong repetition structure.

    Args:
        audio_path: Path to audio file
        hop_length: Hop length for analysis

    Returns:
        Tuple of (repetition_scores, time_per_frame, sample_rate)
        Where repetition_scores[i] is in 0-1 range.
    """
    log.debug("Computing repetition profile for %s", audio_path)

    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # Compute chroma (pitch class) features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

    # Beat-synchronous chroma for more stable analysis
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)

    if len(beat_frames) < 4:
        # Not enough beats; return uniform score
        return np.ones(chroma.shape[1]) * 0.5, hop_length / sr, sr

    # Aggregate chroma at beat resolution
    beat_chroma = librosa.util.sync(chroma, beat_frames, aggregate=np.median)

    # Compute self-similarity matrix
    ssm = librosa.segment.recurrence_matrix(beat_chroma, k=None, width=1,
                                             metric="cosine", sym=True)

    # Compute the lag (diagonal) structure to find repeated patterns
    # Sum along diagonals to find repetition strength at each beat
    n_beats = ssm.shape[0]
    repetition_per_beat = np.zeros(n_beats)

    for i in range(n_beats):
        # Check how similar this beat is to every other beat
        # Count the number of strong recurrence connections
        connections = np.sum(ssm[i, :] > 0)
        repetition_per_beat[i] = connections

    # Normalize to 0-1
    max_conn = repetition_per_beat.max()
    if max_conn > 0:
        repetition_per_beat = repetition_per_beat / max_conn

    # Map back to frame-level
    frame_rate = sr / hop_length
    frames_per_segment = np.diff(np.concatenate([[0], beat_frames,
                                                  [chroma.shape[1]]])).astype(int)

    frame_repetition = np.repeat(repetition_per_beat, frames_per_segment[:len(repetition_per_beat)])

    # Pad or trim to match chroma shape
    if len(frame_repetition) < chroma.shape[1]:
        frame_repetition = np.pad(
            frame_repetition,
            (0, chroma.shape[1] - len(frame_repetition)),
            mode="edge",
        )
    else:
        frame_repetition = frame_repetition[:chroma.shape[1]]

    return frame_repetition, hop_length / sr, sr


def score_segment(audio_path: str, start: float, end: float) -> float:
    """
    Compute a 0-100 repetition score for a specific segment.

    Args:
        audio_path: Path to audio file
        start: Start time in seconds
        end: End time in seconds

    Returns:
        Score from 0-100, where 100 is the most repetition-rich segment.
    """
    rep_profile, time_per_frame, _ = compute_repetition_profile(audio_path)

    start_frame = int(start / time_per_frame)
    end_frame = int(end / time_per_frame)

    # Clamp
    start_frame = max(0, min(start_frame, len(rep_profile) - 1))
    end_frame = max(start_frame + 1, min(end_frame, len(rep_profile)))

    segment = rep_profile[start_frame:end_frame]
    if len(segment) == 0:
        return 0.0

    score = float(np.mean(segment)) * 100.0
    return min(score, 100.0)
