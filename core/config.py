"""
Configuration loader for ringforge.

Loads settings from config/config.toml with sensible defaults.
Uses tomli for TOML parsing (stdlib in Python 3.11+).
"""

import os
import tomli

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "config.toml")
_config_cache = None


def load():
    """Load config.toml from the config directory. Caches the result."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    path = os.path.abspath(_CONFIG_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        _config_cache = tomli.load(f)

    return _config_cache


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
