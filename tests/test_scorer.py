"""
Tests for the scoring engine and individual analyzers.
"""

import numpy as np

from analyzer.energy import compute_energy_profile, score_windows, score_segment
from analyzer.repetition import compute_repetition_profile
from analyzer.beat import compute_beat_profile, get_beat_times
from analyzer.scorer import find_nearest_beat, find_phrase_end


class TestEnergy:
    """Tests for energy analyzer."""

    def test_energy_profile_shape(self, sample_audio_path):
        """Energy profile should return expected structure."""
        rms, time_per_frame, sr = compute_energy_profile(sample_audio_path)
        assert len(rms) > 0
        assert time_per_frame > 0
        assert sr > 0

    def test_score_windows(self, sample_audio_path):
        """score_windows should return sorted results."""
        results = score_windows(sample_audio_path, window_duration=2.0)
        assert len(results) > 0
        for r in results:
            assert "start" in r
            assert "end" in r
            assert "score" in r
            assert 0 <= r["score"] <= 100
        # Should be sorted descending
        scores = [r["score"] for r in results]
        assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_score_segment(self, sample_audio_path):
        """score_segment should return a 0-100 value."""
        score = score_segment(sample_audio_path, 0.0, 3.0)
        assert 0 <= score <= 100


class TestRepetition:
    """Tests for repetition analyzer."""

    def test_repetition_profile_shape(self, sample_audio_path):
        """Repetition profile should return expected structure."""
        profile, time_per_frame, sr = compute_repetition_profile(sample_audio_path)
        assert len(profile) > 0
        assert time_per_frame > 0
        assert sr > 0


class TestBeat:
    """Tests for beat analyzer."""

    def test_beat_profile_shape(self, sample_audio_path):
        """Beat profile should return expected structure."""
        onset_env, beat_times, time_per_frame, sr = compute_beat_profile(sample_audio_path)
        assert len(onset_env) > 0
        assert time_per_frame > 0
        assert sr > 0

    def test_beat_times(self, sample_audio_path):
        """get_beat_times should return a list."""
        beat_times = get_beat_times(sample_audio_path)
        assert isinstance(beat_times, list)


class TestScorerHelpers:
    """Tests for scorer utility functions."""

    def test_find_nearest_beat(self):
        """find_nearest_beat should snap to the closest beat within range."""
        beat_times = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert find_nearest_beat(beat_times, 1.1) == 1.0
        assert find_nearest_beat(beat_times, 4.8) == 5.0
        assert find_nearest_beat(beat_times, 0.1, max_drift=0.5) == 0.1  # too far

    def test_find_nearest_beat_empty(self):
        """Empty beat list should return target unchanged."""
        assert find_nearest_beat([], 2.5) == 2.5

    def test_find_phrase_end(self):
        """find_phrase_end should snap to phrase boundaries."""
        beat_times = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        # Phrase boundaries at index 7 (4.0) and index 15 etc
        result = find_phrase_end(beat_times, 4.2, phrase_length=8, max_drift=1.0)
        assert result == 4.0

    def test_find_phrase_end_too_few_beats(self):
        """Fewer beats than phrase length should return target."""
        beat_times = [0.5, 1.0, 1.5]
        assert find_phrase_end(beat_times, 1.0, phrase_length=8) == 1.0
