"""
YouTube Most Replayed heatmap extractor.

Fetches the YouTube watch page and extracts the "Most Replayed" heatmap data
from the embedded ytInitialData JSON blob. The heatmap shows which parts of
a video are most frequently replayed by viewers.

The approach:
    1. Fetch the YouTube watch page HTML
    2. Extract the ytInitialData JSON variable
    3. Navigate to the markers data structure
    4. Return a list of (time_seconds, intensity_normalized) pairs
"""

import json
import re
import time

import requests

from core.cache import video_id_from_url, save_heatmap, load_heatmap
from core.logging import get_logger

log = get_logger()

# YouTube watch page URL template
_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"

# Regex to find ytInitialData in the page HTML
_INITIAL_DATA_RE = re.compile(
    r'ytInitialData\s*=\s*({.*?})\s*;</script>',
    re.DOTALL,
)

# User-agent to avoid being blocked
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_heatmap(video_id: str, force: bool = False) -> list[dict] | None:
    """
    Fetch the Most Replayed heatmap for a YouTube video.

    Args:
        video_id: YouTube video ID (e.g. 'dQw4w9WgXcQ')
        force: If True, re-fetch even if cached

    Returns:
        List of dicts with keys 'time' (seconds) and 'intensity' (0.0-1.0),
        sorted by time. Returns None if heatmap data is not available.
    """
    # Check cache first
    if not force:
        cached = load_heatmap(video_id)
        if cached and "markers" in cached:
            log.debug("Using cached heatmap for %s", video_id)
            return cached["markers"]

    log.info("Fetching heatmap for video %s", video_id)

    # Step 1: Fetch the YouTube watch page
    url = _WATCH_URL.format(video_id=video_id)
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()

    html = resp.text

    # Step 2: Extract ytInitialData JSON
    match = _INITIAL_DATA_RE.search(html)
    if not match:
        log.warning("Could not find ytInitialData on page for %s", video_id)
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        log.warning("Failed to parse ytInitialData JSON: %s", e)
        return None

    # Step 3: Navigate to the heatmap markers
    markers = _extract_heatmap_markers(data)
    if markers is None:
        log.info("No heatmap markers found for video %s", video_id)
        return None

    # Step 4: Cache the result
    save_heatmap(video_id, {"markers": markers, "fetched_at": time.time()})

    log.info("Found %d heatmap markers for %s", len(markers), video_id)
    return markers


def _extract_heatmap_markers(data: dict) -> list[dict] | None:
    """
    Navigate the ytInitialData structure to find heatmap markers.

    Current YouTube structure (as of 2026):
        frameworkUpdates
          -> entityBatchUpdate
            -> mutations[] (array of entity mutations)
              -> payload.macroMarkersListEntity.markersList.markers[]
                Each marker has:
                  - startMillis: str (milliseconds)
                  - durationMillis: str (milliseconds)
                  - intensityScoreNormalized: float (0.0-1.0)

    Returns:
        List of {time: float, intensity: float} sorted by time, or None.
    """
    try:
        mutations = data["frameworkUpdates"]["entityBatchUpdate"]["mutations"]
    except (KeyError, TypeError):
        return None

    markers = []
    for mutation in mutations:
        payload = mutation.get("payload", {})
        markers_list = (payload
                        .get("macroMarkersListEntity", {})
                        .get("markersList", {}))
        if not markers_list:
            continue

        raw_markers = markers_list.get("markers", [])
        for marker in raw_markers:
            try:
                start_ms = int(marker["startMillis"])
                intensity = float(marker["intensityScoreNormalized"])

                markers.append({
                    "time": start_ms / 1000.0,
                    "intensity": intensity,  # already 0.0-1.0
                })
            except (KeyError, TypeError, ValueError):
                continue

    if not markers:
        return None

    markers.sort(key=lambda m: m["time"])
    return markers


def get_peak_segment(markers: list[dict],
                     duration: float = 30.0,
                     min_start: float = 0.0,
                     max_end: float | None = None) -> dict | None:
    """
    Find the highest-intensity segment of a given duration from the heatmap.

    Uses a sliding window over the heatmap markers and selects the window
    with the highest average intensity.

    Args:
        markers: List of {time, intensity} dicts from fetch_heatmap()
        duration: Desired segment duration in seconds
        min_start: Earliest allowed start time
        max_end: Latest allowed end time (defaults to the last marker time)

    Returns:
        Dict with keys 'start', 'end', 'avg_intensity', or None if no markers.
    """
    if not markers:
        return None

    if max_end is None:
        max_end = markers[-1]["time"]

    # Compute the total intensity from markers within each candidate window
    # Walk through each marker as a potential window start
    best = None
    best_score = -1.0

    for i, start_marker in enumerate(markers):
        window_start = start_marker["time"]

        # Skip if outside allowed range
        if window_start < min_start:
            continue
        if window_start + duration > max_end:
            break

        # Sum intensities of markers within this window
        total_intensity = 0.0
        count = 0
        for m in markers[i:]:
            if m["time"] > window_start + duration:
                break
            total_intensity += m["intensity"]
            count += 1

        if count == 0:
            continue

        avg = total_intensity / count
        if avg > best_score:
            best_score = avg
            best = {
                "start": window_start,
                "end": window_start + duration,
                "avg_intensity": avg,
            }

    return best
