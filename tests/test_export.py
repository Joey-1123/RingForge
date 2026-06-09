"""
Tests for export module and config loading.
"""

import os

from pydub import AudioSegment

from core.config import load, get_weights, get_profile
from audio.export import export_profile, get_supported_profiles


class TestConfig:
    """Tests for configuration loading."""

    def test_load(self):
        """Config should load successfully."""
        cfg = load()
        assert "default_duration" in cfg
        assert "weights" in cfg
        assert "profiles" in cfg

    def test_weights_default(self):
        """Default weights should sum to ~1.0."""
        weights = get_weights(heatmap_available=True)
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_weights_no_heatmap(self):
        """No-heatmap weights should sum to ~1.0."""
        weights = get_weights(heatmap_available=False)
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_get_profile(self):
        """get_profile should return profile config."""
        android = get_profile("android")
        assert android["codec"] == "mp3"
        assert android["bitrate"] == "192k"

    def test_get_supported_profiles(self):
        """Should list all profile names."""
        profiles = get_supported_profiles()
        assert "android" in profiles
        assert "iphone" in profiles
        assert "notification" in profiles


class TestExport:
    """Tests for the export module."""

    def test_export_android(self, sample_audio_path, tmp_path):
        """Exporting as android profile should produce an MP3 file."""
        audio = AudioSegment.from_file(sample_audio_path)
        output = export_profile(audio, "android", output_dir=str(tmp_path))
        assert os.path.exists(output)
        assert output.endswith(".mp3")
        assert os.path.getsize(output) > 0

    def test_export_notification(self, sample_audio_path, tmp_path):
        """Exporting as notification should produce a shorter-like file."""
        audio = AudioSegment.from_file(sample_audio_path)
        output = export_profile(audio, "notification",
                                output_dir=str(tmp_path), base_name="test")
        assert os.path.exists(output)
        assert os.path.getsize(output) > 0
