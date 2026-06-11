"""
Cache manager for ringforge.

Structures:
    cache/{video_id}/
        audio.wav         - downloaded audio in canonical WAV format
        metadata.json     - video metadata (title, duration, etc.)
        heatmap.json      - YouTube heatmap data if available
        analysis.json     - computed analysis scores for candidate segments
"""

import json
import os
import hashlib

_CACHE_ROOT = os.path.join(os.path.dirname(__file__), "..", "cache")


def _ensure_dir(video_id: str) -> str:
    """Create and return the cache directory for a given video ID."""
    path = os.path.join(_CACHE_ROOT, video_id)
    os.makedirs(path, exist_ok=True)
    return path


def cache_key_from_url(url: str) -> str:
    """Generate a stable cache key from a URL (YouTube or otherwise)."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def cache_key_from_path(file_path: str) -> str:
    """Generate a cache key from a local file path + modification time."""
    abspath = os.path.abspath(file_path)
    mtime = os.path.getmtime(file_path)
    return hashlib.sha256(f"{abspath}:{mtime}".encode()).hexdigest()[:16]


def video_id_from_url(url: str) -> str:
    """Deprecated alias for cache_key_from_url."""
    return cache_key_from_url(url)


def get_audio_path(video_id: str) -> str:
    """Return the expected path for the cached audio file."""
    return os.path.join(_CACHE_ROOT, video_id, "audio.wav")


def save_metadata(video_id: str, data: dict):
    """Save metadata dict as JSON."""
    path = os.path.join(_ensure_dir(video_id), "metadata.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_metadata(video_id: str) -> dict | None:
    """Load cached metadata, or None if missing."""
    path = os.path.join(_CACHE_ROOT, video_id, "metadata.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def save_heatmap(video_id: str, data: dict):
    """Save heatmap analysis results."""
    path = os.path.join(_ensure_dir(video_id), "heatmap.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_heatmap(video_id: str) -> dict | None:
    """Load cached heatmap data, or None."""
    path = os.path.join(_CACHE_ROOT, video_id, "heatmap.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def save_analysis(video_id: str, data: dict):
    """Save the full analysis result (top-5 segments, scores, etc.)."""
    path = os.path.join(_ensure_dir(video_id), "analysis.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_analysis(video_id: str) -> dict | None:
    """Load cached analysis."""
    path = os.path.join(_CACHE_ROOT, video_id, "analysis.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def exists(video_id: str) -> bool:
    """Check if audio is already cached for this video ID."""
    return os.path.exists(get_audio_path(video_id))
