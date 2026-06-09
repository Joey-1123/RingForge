"""
Export audio files per named profiles.

Each profile defines codec, bitrate, effects, and output extension.
This module is the clean interface between the generation pipeline
and file output.
"""

import os

from pydub import AudioSegment

from core.config import get_profile, load as load_config
from core.logging import get_logger
from audio.effects import apply_all

log = get_logger()


def export_profile(audio: AudioSegment,
                   profile_name: str,
                   output_dir: str | None = None,
                   base_name: str = "ringtone") -> str:
    """
    Export an AudioSegment using the settings from a named profile.

    Args:
        audio: The AudioSegment to export
        profile_name: One of 'android', 'iphone', 'notification', 'alarm', 'tiktok'
        output_dir: Directory to save to (defaults to exports/)
        base_name: Base filename (without extension)

    Returns:
        Path to the exported file.
    """
    cfg = load_config()
    profile = cfg.get("profiles", {}).get(profile_name, {})
    profile_cfg = profile

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "exports")
    os.makedirs(output_dir, exist_ok=True)

    # Apply profile effects
    processed = apply_all(
        audio,
        do_normalize=True,
        do_fade=True,
        do_bass=profile_cfg.get("bass_boost", False),
        normalize_db=profile_cfg.get("normalize_db", -1.0),
        fade_ms=profile_cfg.get("fade_ms", 200),
    )

    # Determine format and extension
    codec = profile_cfg.get("codec", "mp3")
    ext = profile_cfg.get("extension", codec)

    output_path = os.path.join(output_dir, f"{base_name}_{profile_name}.{ext}")

    # For AAC/m4r, we need to use mp4 format with the right codec
    export_format = codec
    if codec == "aac":
        export_format = "mp4"
    elif codec == "adts":
        export_format = "adts"

    bitrate = profile_cfg.get("bitrate", "192k")

    log.info("Exporting to %s [%s, %s]", output_path, export_format, bitrate)
    processed.export(
        output_path,
        format=export_format,
        bitrate=bitrate,
        parameters=["-write_xing", "0"] if codec == "mp3" else [],
    )

    return output_path


def get_supported_profiles() -> list[str]:
    """Return the list of available export profile names."""
    cfg = load_config()
    return list(cfg.get("profiles", {}).keys())


def get_profile_info(profile_name: str) -> dict:
    """Return the configuration dict for a profile."""
    return get_profile(profile_name)
