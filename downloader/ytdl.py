"""
YouTube downloader using yt-dlp.

Downloads the best available audio stream and converts it to 44.1kHz WAV.
Caches results locally to avoid re-downloading.
"""

import json
import os
import subprocess
import sys

from core.cache import video_id_from_url, get_audio_path, save_metadata, load_metadata, exists
from core.logging import get_logger

try:
    import yt_dlp  # noqa: F401 — check availability
    _YTDLP_AVAILABLE = True
except ImportError:
    _YTDLP_AVAILABLE = False

log = get_logger()


def download(url: str, force: bool = False) -> str:
    """
    Download audio from a YouTube URL and return the path to a WAV file.

    If the audio is already cached, skip the download unless force=True.
    Also saves video metadata (title, duration, etc.) alongside the audio.
    """
    if not _YTDLP_AVAILABLE:
        log.error("yt-dlp is not installed. Install it with: uv sync --extra youtube")
        raise RuntimeError(
            "yt-dlp is required to download from YouTube. "
            "Install it with: uv sync --extra youtube"
        )

    video_id = video_id_from_url(url)
    output_path = get_audio_path(video_id)

    if exists(video_id) and not force:
        log.info("Using cached audio for %s", url)
        return output_path

    # Step 1: Download best audio as a temp file using yt-dlp
    log.info("Downloading audio from %s", url)
    temp_dir = os.path.dirname(output_path)
    os.makedirs(temp_dir, exist_ok=True)

    # yt-dlp will output to a temp file; we rename later
    temp_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

    download_cmd = [
        sys.executable, "-m", "yt_dlp",
        "--extract-audio",
        "--audio-format", "wav",
        "--audio-quality", "0",          # best quality
        "--output", temp_template,
        "--print", "after_move:%(filepath)j",  # prints the actual output path as JSON string
        "--no-playlist",
        "--quiet",
        url,
    ]

    result = subprocess.run(
        download_cmd,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout for downloads
    )

    if result.returncode != 0:
        log.error("yt-dlp failed: %s", result.stderr)
        raise RuntimeError(f"Download failed: {result.stderr}")

    # Step 2: Locate the downloaded file
    # yt-dlp --print after_move prints the final filepath as JSON
    # Parse it from stdout (last line usually)
    lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    if not lines:
        raise RuntimeError("yt-dlp did not report an output file path")

    import json as _json
    dl_path = _json.loads(lines[-1])

    # Step 3: Ensure it is our canonical name
    if dl_path != output_path:
        os.replace(dl_path, output_path)

    # Step 4: Fetch metadata (separate yt-dlp call for JSON info)
    info_cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--no-playlist",
        "--quiet",
        url,
    ]
    info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=60)
    if info_result.returncode == 0 and info_result.stdout.strip():
        metadata = json.loads(info_result.stdout.strip().splitlines()[0])
        save_metadata(video_id, {
            "title": metadata.get("title"),
            "duration": metadata.get("duration"),
            "channel": metadata.get("channel"),
            "uploader": metadata.get("uploader"),
            "thumbnail": metadata.get("thumbnail"),
            "webpage_url": metadata.get("webpage_url"),
            "video_id": metadata.get("id"),
        })

    log.info("Downloaded to %s", output_path)
    return output_path


def get_metadata(url: str) -> dict | None:
    """Return metadata dict for a URL without downloading audio."""
    video_id = video_id_from_url(url)
    cached = load_metadata(video_id)
    if cached:
        return cached

    # We can also fetch metadata directly via --dump-json
    info_cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--no-playlist",
        "--quiet",
        url,
    ]
    result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        log.warning("Failed to fetch metadata: %s", result.stderr)
        return None

    data = json.loads(result.stdout.strip().splitlines()[0])
    metadata = {
        "title": data.get("title"),
        "duration": data.get("duration"),
        "channel": data.get("channel"),
        "uploader": data.get("uploader"),
        "thumbnail": data.get("thumbnail"),
        "webpage_url": data.get("webpage_url"),
        "video_id": data.get("id"),
    }
    save_metadata(video_id, metadata)
    return metadata
