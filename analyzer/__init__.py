"""
Analyzer module exports for ringforge.
"""

from analyzer._context import SignalContext
from analyzer.energy import compute_energy_profile, score_windows, score_segment
from analyzer.repetition import compute_repetition_profile
from analyzer.beat import compute_beat_profile, get_beat_times
from analyzer.scorer import find_nearest_beat, find_phrase_end, compute_scores
from analyzer.heatmap import fetch_heatmap, get_peak_segment
from analyzer.metadata import analyze_audio

__all__ = [
    "SignalContext",
    "compute_energy_profile",
    "score_windows",
    "score_segment",
    "compute_repetition_profile",
    "compute_beat_profile",
    "get_beat_times",
    "find_nearest_beat",
    "find_phrase_end",
    "compute_scores",
    "fetch_heatmap",
    "get_peak_segment",
    "analyze_audio",
]
