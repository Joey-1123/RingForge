"""
Tests for the heatmap analyzer (without network requests).
"""

from analyzer.heatmap import get_peak_segment


class TestHeatmap:
    """Tests for heatmap analysis functions."""

    def test_get_peak_segment_basic(self):
        """get_peak_segment should find the highest-intensity window."""
        markers = [
            {"time": 0.0, "intensity": 0.1},
            {"time": 5.0, "intensity": 0.2},
            {"time": 10.0, "intensity": 0.9},
            {"time": 15.0, "intensity": 0.8},
            {"time": 20.0, "intensity": 0.3},
            {"time": 25.0, "intensity": 0.1},
            {"time": 30.0, "intensity": 0.05},
        ]
        best = get_peak_segment(markers, duration=10.0)
        assert best is not None
        # The 10-20 range has the highest average intensity (0.85)
        assert abs(best["start"] - 10.0) < 1.0
        assert abs(best["end"] - 20.0) < 1.0
        assert best["avg_intensity"] > 0.5

    def test_get_peak_segment_empty(self):
        """Empty markers should return None."""
        assert get_peak_segment([], duration=10.0) is None

    def test_get_peak_segment_min_start(self):
        """min_start should exclude windows before it."""
        markers = [
            {"time": 0.0, "intensity": 1.0},
            {"time": 5.0, "intensity": 1.0},
            {"time": 10.0, "intensity": 1.0},
            {"time": 15.0, "intensity": 0.1},
        ]
        best = get_peak_segment(markers, duration=5.0, min_start=8.0)
        assert best is not None
        assert best["start"] >= 8.0

    def test_get_peak_segment_max_end(self):
        """max_end should exclude windows after it."""
        markers = [
            {"time": 0.0, "intensity": 0.1},
            {"time": 5.0, "intensity": 0.1},
            {"time": 10.0, "intensity": 1.0},
            {"time": 15.0, "intensity": 1.0},
        ]
        best = get_peak_segment(markers, duration=5.0, max_end=12.0)
        assert best is not None
        assert best["end"] <= 12.0
