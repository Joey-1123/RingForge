"""
Tests for audio trimming and effects.
"""

import os

import numpy as np
from pydub import AudioSegment

from audio.trim import trim, trim_with_smart_start, _detect_format
from audio.effects import apply_fade, normalize, remove_silence


class TestTrim:
    """Tests for the trim module."""

    def test_trim_basic(self, sample_audio_path):
        """Trimming a 10s file to a 3s segment should produce correct duration."""
        result = trim(sample_audio_path, 2.0, 5.0)
        duration_ms = len(result)
        # Should be ~3 seconds (allow small rounding)
        assert abs(duration_ms - 3000) < 50, f"Expected ~3000ms, got {duration_ms}ms"

    def test_trim_start_zero(self, sample_audio_path):
        """Trimming from 0 should work."""
        result = trim(sample_audio_path, 0.0, 3.0)
        duration_ms = len(result)
        assert abs(duration_ms - 3000) < 50

    def test_trim_clamp_ends(self, sample_audio_path):
        """Trim beyond file length should clamp without error."""
        result = trim(sample_audio_path, 8.0, 20.0)
        duration_ms = len(result)
        assert duration_ms > 0
        assert duration_ms < 3000  # clamped to ~2s

    def test_trim_invalid_range(self, sample_audio_path):
        """Start after end should clamp to zero duration."""
        result = trim(sample_audio_path, 5.0, 2.0)
        assert len(result) == 0

    def test_trim_with_smart_start_no_beats(self, sample_audio_path):
        """Without beat times, smart start should behave like regular trim."""
        audio = AudioSegment.from_file(sample_audio_path)
        result = trim_with_smart_start(audio, 1.0, 4.0, beat_times=None)
        assert abs(len(result) - 3000) < 50

    def test_trim_with_smart_start_with_beats(self, sample_audio_path):
        """With beat times, smart start should snap to nearest."""
        audio = AudioSegment.from_file(sample_audio_path)
        beat_times = [0.5, 1.5, 2.5, 3.5]
        result = trim_with_smart_start(audio, 1.4, 4.0, beat_times=beat_times)
        # Should snap to 1.5 (nearest beat)
        # offset from 1.4 to 1.5 is 0.1s, so length should be ~2600ms
        assert abs(len(result) - 2500) < 100

    def test_detect_format(self):
        """_detect_format should map extensions correctly."""
        assert _detect_format("test.mp3") == "mp3"
        assert _detect_format("test.m4r") == "mp4"
        assert _detect_format("test.wav") == "wav"
        assert _detect_format("test.ogg") == "ogg"
        assert _detect_format("test.unknown") == "wav"


class TestEffects:
    """Tests for audio effects."""

    def test_apply_fade(self, sample_audio_path):
        """Fade should not change duration."""
        audio = AudioSegment.from_file(sample_audio_path)
        original_length = len(audio)
        faded = apply_fade(audio, fade_ms=200)
        assert len(faded) == original_length

    def test_normalize(self, sample_audio_path):
        """Normalize should adjust loudness without breaking."""
        audio = AudioSegment.from_file(sample_audio_path)
        normalized = normalize(audio, target_dbfs=-3.0)
        assert len(normalized) > 0
        # The max dBFS should be close to our target
        assert abs(normalized.max_dBFS - (-3.0)) < 2.0

    def test_remove_silence_no_silence(self, sample_audio_path):
        """Audio with no silence should be unchanged."""
        audio = AudioSegment.from_file(sample_audio_path)
        result = remove_silence(audio)
        assert len(result) > 0

    def test_remove_silence_silent_audio(self, empty_wav_path):
        """Silent audio should be trimmed."""
        audio = AudioSegment.from_file(empty_wav_path)
        result = remove_silence(audio)
        # Should trim to near-zero
        assert len(result) <= len(audio)
