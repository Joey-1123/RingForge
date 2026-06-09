"""
Pytest configuration and shared fixtures for RingForge tests.
"""

import os
import tempfile

import numpy as np
import pytest
from scipy.io import wavfile


@pytest.fixture(scope="session")
def sample_audio_path():
    """
    Generate a short synthetic WAV file for testing.

    The audio is a 10-second sine wave sweep + noise, which gives
    enough variation for analyzer tests.
    """
    sr = 22050
    duration = 10.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Frequency sweep from 200Hz to 800Hz
    sweep = np.sin(2 * np.pi * (200 + 600 * t / duration) * t)

    # Add some percussive clicks at 2s and 5s for beat detection
    clicks = np.zeros_like(t)
    click_indices = [int(2 * sr), int(5 * sr)]
    for ci in click_indices:
        clicks[ci:ci + int(0.05 * sr)] = 0.8 * np.hanning(int(0.05 * sr))

    # Add noise
    noise = np.random.randn(len(t)) * 0.05

    audio = sweep + clicks + noise

    # Normalize to 16-bit range
    audio = audio / np.max(np.abs(audio)) * 0.9
    audio_int16 = (audio * 32767).astype(np.int16)

    # Write to temp file
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wavfile.write(path, sr, audio_int16)

    yield path

    os.unlink(path)


@pytest.fixture
def empty_wav_path():
    """
    Generate a very short (0.5s) silent WAV for edge case tests.
    """
    sr = 22050
    duration = 0.5
    audio = np.zeros(int(sr * duration), dtype=np.int16)

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wavfile.write(path, sr, audio)

    yield path

    os.unlink(path)
