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
        "--print", "after_move:%(filepath)j",  # prints filepath to stdout
        "--no-playlist",
        "--quiet",
        "--no-update",                   # suppress outdated version warning
        "--js-runtimes", "node",         # use Node.js instead of deno
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

    # Parse --print after_move output (first line of stdout)
    lines = [l.strip().strip('"').strip("'") for l in result.stdout.splitlines() if l.strip()]
    if not lines:
        raise RuntimeError("yt-dlp did not report an output file path")
    dl_path = lines[0]

    # Ensure canonical name
    if dl_path != output_path:
        os.replace(dl_path, output_path)

    # Fetch metadata — get_metadata() checks cache first, so this
    # will only spawn a yt-dlp subprocess if not already cached.
    # Called here so that the subsequent get_metadata() call in
    # cli.py returns cached data without another subprocess.
    get_metadata(url)

    log.info("Downloaded to %s", output_path)
    return output_path


def get_metadata(url: str) -> dict | None:
    """Return metadata dict for a URL without downloading audio.

    Checks cache first — if download() was called before this,
    returns cached data without spawning another yt-dlp subprocess.
    """
    video_id = video_id_from_url(url)
    cached = load_metadata(video_id)
    if cached:
        return cached

    # Only fetch from yt-dlp if not already cached
    info_cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--no-playlist",
        "--quiet",
        "--no-update",
        "--js-runtimes", "node",
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
