"""
Shared signal context for ringforge analyzers.

Loads audio once via librosa.load() and pre-computes all analysis profiles
(energy, onset, beat, repetition). All analyzers read from this shared context
instead of loading the audio file independently.
"""

import numpy as np
import librosa

from core.logging import get_logger

log = get_logger()

# Default hop length used across all analyzers
DEFAULT_HOP_LENGTH = 512


class SignalContext:
    """
    Loads audio once and exposes pre-computed signal arrays and profiles.

    Attributes:
        audio_path: The source audio file path.
        y: Mono audio samples (np.ndarray).
        sr: Sample rate.
        hop_length: Hop length for frame-level analysis.
        time_per_frame: Seconds per frame.
        energy: RMS energy envelope (np.ndarray).
        onset_env: Onset strength envelope (np.ndarray).
        beat_times: List of beat onset times in seconds.
        repetition: Repetition salience profile (np.ndarray).
    """

    def __init__(self, audio_path: str, hop_length: int = DEFAULT_HOP_LENGTH):
        log.debug("Loading audio once: %s", audio_path)
        self.audio_path = audio_path
        self.hop_length = hop_length

        # Single load — shared across all analyzers
        self.y, self.sr = librosa.load(audio_path, sr=None, mono=True)
        self.time_per_frame = hop_length / self.sr

        # Pre-compute energy profile
        self.energy = librosa.feature.rms(y=self.y, hop_length=hop_length)[0]

        # Pre-compute onset strength (used by beat + novelty)
        self.onset_env = librosa.onset.onset_strength(y=self.y, sr=self.sr,
                                                       hop_length=hop_length)
        onset_max = self.onset_env.max()
        if onset_max > 0:
            self.onset_env = self.onset_env / onset_max

        # Pre-compute beat times
        _, beat_frames = librosa.beat.beat_track(
            onset_envelope=self.onset_env, sr=self.sr, hop_length=hop_length
        )
        self.beat_times = list(librosa.frames_to_time(
            beat_frames, sr=self.sr, hop_length=hop_length
        ))

        # Pre-compute repetition profile
        self.repetition = self._compute_repetition()

    def _compute_repetition(self) -> np.ndarray:
        """Compute beat-synchronous chroma self-similarity matrix."""
        chroma = librosa.feature.chroma_cqt(y=self.y, sr=self.sr,
                                            hop_length=self.hop_length)
        tempo, beat_frames = librosa.beat.beat_track(
            y=self.y, sr=self.sr, hop_length=self.hop_length
        )
        if len(beat_frames) < 4:
            return np.ones(chroma.shape[1]) * 0.5

        beat_chroma = librosa.util.sync(chroma, beat_frames, aggregate=np.median)
        ssm = librosa.segment.recurrence_matrix(
            beat_chroma, k=None, width=1, metric="cosine", sym=True
        )
        n_beats = ssm.shape[0]
        repetition_per_beat = np.zeros(n_beats)
        for i in range(n_beats):
            repetition_per_beat[i] = np.sum(ssm[i, :] > 0)

        max_conn = repetition_per_beat.max()
        if max_conn > 0:
            repetition_per_beat = repetition_per_beat / max_conn

        # Map back to frame-level
        frame_rate = self.sr / self.hop_length
        frames_per_segment = np.diff(np.concatenate(
            [[0], beat_frames, [chroma.shape[1]]]
        )).astype(int)
        frame_repetition = np.repeat(repetition_per_beat,
                                     frames_per_segment[:len(repetition_per_beat)])
        if len(frame_repetition) < chroma.shape[1]:
            frame_repetition = np.pad(
                frame_repetition,
                (0, chroma.shape[1] - len(frame_repetition)),
                mode="edge",
            )
        else:
            frame_repetition = frame_repetition[:chroma.shape[1]]

        return frame_repetition

    # ---- Convenience accessors matching old analyzer function signatures ----

    def get_energy_profile(self) -> tuple[np.ndarray, float, int]:
        """Return (energy_array, time_per_frame, sample_rate)."""
        return self.energy, self.time_per_frame, self.sr

    def get_onset_env(self) -> tuple[np.ndarray, float, int]:
        """Return (onset_env, time_per_frame, sample_rate)."""
        return self.onset_env, self.time_per_frame, self.sr

    def get_beat_profile(self) -> tuple[np.ndarray, list[float], float, int]:
        """Return (onset_env, beat_times, time_per_frame, sample_rate)."""
        return self.onset_env, self.beat_times, self.time_per_frame, self.sr

    def get_repetition_profile(self) -> tuple[np.ndarray, float, int]:
        """Return (repetition_array, time_per_frame, sample_rate)."""
        return self.repetition, self.time_per_frame, self.sr

    def get_duration(self) -> float:
        """Total audio duration in seconds."""
        return librosa.get_duration(y=self.y, sr=self.sr)
