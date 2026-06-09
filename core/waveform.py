"""
Waveform data generation for preview and visualization.

Produces a downsampled waveform representation that can be used for:
    - ASCII waveform in the CLI
    - Rendering in the PySide6 GUI (Phase 7)
    - Saving as JSON for external use
"""

import numpy as np
import librosa

from core.logging import get_logger

log = get_logger()


def extract_waveform(audio_path: str, num_points: int = 1000) -> dict:
    """
    Load audio and compute a simplified waveform.

    Args:
        audio_path: Path to an audio file
        num_points: Number of sample points for the waveform summary

    Returns:
        Dict with keys:
            - samples: list of float values (-1 to 1) of length num_points
            - sample_rate: int
            - duration: float (seconds)
            - channels: int
    """
    log.debug("Extracting waveform from %s (%d points)", audio_path, num_points)

    # Load mono audio
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # Downsample to num_points by averaging frames
    frame_size = max(1, len(y) // num_points)
    # Trim to exact multiple
    trimmed_len = frame_size * (len(y) // frame_size)
    y_trimmed = y[:trimmed_len]

    # Reshape and compute RMS per frame
    frames = y_trimmed.reshape(-1, frame_size)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))

    # Normalize to 0-1 range
    max_val = rms.max()
    if max_val > 0:
        rms = rms / max_val

    return {
        "samples": rms.tolist(),
        "sample_rate": int(sr),
        "duration": duration,
        "channels": 1 if y.ndim == 1 else y.shape[0],
    }


def ascii_waveform(waveform: dict, width: int = 60, height: int = 5) -> str:
    """
    Render a simple ASCII waveform visualization.

    Args:
        waveform: Output from extract_waveform()
        width: Number of characters wide
        height: Number of lines tall

    Returns:
        Multi-line string of the ASCII waveform.
    """
    samples = np.array(waveform["samples"])

    # Downsample to desired width
    indices = np.linspace(0, len(samples) - 1, width, dtype=int)
    downsampled = samples[indices]

    # Build the waveform line by line
    lines = []
    for row in range(height - 1, -1, -1):
        threshold = (row + 1) / height
        line_chars = []
        for val in downsampled:
            if val >= threshold:
                line_chars.append("#")
            elif val >= threshold - (1.0 / height) * 0.5:
                line_chars.append("-")
            else:
                line_chars.append(" ")
        lines.append("".join(line_chars))

    return "\n".join(lines)
