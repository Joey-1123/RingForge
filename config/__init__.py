"""
Config module exports for ringforge.
"""

from core.config import load as load_config, get_profile, get_weight

__all__ = [
    "load_config",
    "get_profile",
    "get_weight",
]
