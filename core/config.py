"""
Configuration loader for ringforge.

Loads settings from config/config.toml with sensible defaults.
Uses tomli for TOML parsing (stdlib in Python 3.11+).
"""

import os
import tomli

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "config.toml")
_config_cache = None


def _config_file_path() -> str:
    return os.path.abspath(_CONFIG_PATH)


def load():
    """Load config.toml from the config directory. Caches the result."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    path = _config_file_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        _config_cache = tomli.load(f)

    return _config_cache


def invalidate_cache():
    """Clear the cached config so the next load() re-reads from disk."""
    global _config_cache
    _config_cache = None


def save(cfg: dict):
    """Write the config dict back to config.toml and invalidate cache."""
    import tomli_w

    path = _config_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(cfg, f)
    invalidate_cache()


def get_weights(heatmap_available: bool) -> dict:
    """
    Return scoring weights based on whether heatmap data is available.
    Returns a dict with keys: replay, repetition, energy, beat, novelty.
    """
    cfg = load()
    key = "default" if heatmap_available else "no_heatmap"
    return cfg["weights"][key]


def get_profile(name: str) -> dict:
    """Return a single export profile by name (e.g. 'android', 'iphone')."""
    cfg = load()
    return cfg["profiles"][name]


def get_defaults() -> dict:
    """Return the top-level default settings."""
    cfg = load()
    return {
        "default_duration": cfg.get("default_duration", 30),
        "default_profile": cfg.get("default_profile", "android"),
        "normalize": cfg.get("normalize", True),
        "fade": cfg.get("fade", True),
        "cache": cfg.get("cache", True),
        "log_level": cfg.get("log_level", "INFO"),
    }
