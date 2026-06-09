"""
CLI entry point for ringforge.

Provides commands:
    download   - download and cache audio
    preview    - play a segment of a video
    generate   - auto-detect the best segment and export
    export     - convert a file per export profile
    info       - show video metadata
    batch      - process multiple URLs from a file
    gui        - launch desktop GUI
"""

import os
import sys

import click

from core.logging import setup as setup_logging, get_logger
from core.config import load as load_config
from core.waveform import extract_waveform, ascii_waveform
from downloader import ytdl
from audio.trim import trim, trim_with_smart_start
from audio.effects import apply_all


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------

_url_arg = click.argument("url")
_start_opt = click.option("--start", type=float, default=None,
                          help="Start time in seconds")
_end_opt = click.option("--end", type=float, default=None,
                        help="End time in seconds")
_duration_opt = click.option("--duration", type=float, default=None,
                             help="Duration in seconds (alternative to --end)")
_force_opt = click.option("--force", is_flag=True, default=False,
                          help="Re-download even if cached")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_times(start, end, duration, total_duration):
    """
    Convert CLI time arguments to (start, end) in seconds.

    Priority:
        1. If start and end given, use those
        2. If start and duration given, compute end = start + duration
        3. If start only and total_duration known, set end = total_duration
        4. If nothing given, (None, None)
    """
    if start is not None and end is not None:
        return start, end
    if start is not None and duration is not None:
        return start, start + duration
    if start is not None and total_duration:
        return start, float(total_duration)
    if start is None and duration is not None:
        return 0.0, duration
    return start, end


def _exports_dir():
    """Return the path to the exports directory, creating it if needed."""
    path = os.path.join(os.path.dirname(__file__), "..", "exports")
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# CLI Group
# ---------------------------------------------------------------------------

@click.group()
@click.option("--log-level", default=None, help="Log level (DEBUG, INFO, etc.)")
def main(log_level):
    """RingForge: Find the best moment in any audio and export it."""
    cfg = load_config()
    level = log_level or cfg.get("log_level", "INFO")
    setup_logging(level)


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

@main.command()
@_url_arg
@_force_opt
def download(url, force):
    """Download audio from a YouTube URL and cache it locally."""
    path = ytdl.download(url, force=force)
    click.echo(path)


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

@main.command()
@_url_arg
def info(url):
    """Show metadata for a YouTube video."""
    meta = ytdl.get_metadata(url)
    if not meta:
        click.echo("Could not fetch metadata.", err=True)
        sys.exit(1)

    click.echo(f"Title:     {meta.get('title', 'N/A')}")
    click.echo(f"Channel:   {meta.get('channel', meta.get('uploader', 'N/A'))}")
    dur = meta.get("duration", 0)
    minutes, seconds = divmod(int(dur), 60)
    click.echo(f"Duration:  {minutes}m {seconds}s")
    click.echo(f"Video ID:  {meta.get('video_id', 'N/A')}")
    if meta.get("thumbnail"):
        click.echo(f"Thumbnail: {meta['thumbnail']}")

    # Show audio analysis if cached
    from core.cache import video_id_from_url, get_audio_path, exists
    vid = video_id_from_url(url)
    if exists(vid):
        audio_path = get_audio_path(vid)
        try:
            from analyzer.metadata import analyze_audio
            analysis = analyze_audio(audio_path)
            click.echo("")
            click.echo("--- Audio Analysis ---")
            if analysis.get("tempo"):
                click.echo(f"Tempo:     {analysis['tempo']:.1f} BPM")
            if analysis.get("key"):
                click.echo(f"Key:       {analysis['key']}")
            if analysis.get("loudness") is not None:
                click.echo(f"Loudness:  {analysis['loudness']:.1f} dB")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# generate (the main command)
# ---------------------------------------------------------------------------

@main.command()
@_url_arg
@click.option("--mode", type=click.Choice(["manual", "heatmap", "auto", "notification"]),
              default="auto", help="Selection mode")
@click.option("--profile", type=click.Choice(
    ["android", "iphone", "notification", "alarm", "tiktok"]),
    default=None, help="Export profile")
@_start_opt
@_end_opt
@_duration_opt
@_force_opt
def generate(url, mode, profile, start, end, duration, force):
    """
    Generate a ringtone from a YouTube URL.

    Modes:
      manual       - requires --start and --end or --duration
      heatmap      - uses YouTube Most Replayed heatmap
      auto         - full AI scoring pipeline (default)
      notification - finds a short punchy segment (3-8s)
    """
    log = get_logger()
    cfg = load_config()
    _log = log  # unused but available

    # Resolve profile
    if profile is None:
        profile = cfg.get("default_profile", "android")

    # Step 1: Download if needed
    audio_path = ytdl.download(url, force=force)

    if mode == "manual":
        # Resolve times from CLI arguments
        meta = ytdl.get_metadata(url)
        total_dur = meta.get("duration") if meta else None
        s, e = _resolve_times(start, end, duration, total_dur)

        if s is None or e is None:
            click.echo(
                "Error: manual mode requires --start and --end (or --duration).",
                err=True,
            )
            sys.exit(1)

        if s >= e:
            click.echo("Error: start must be before end.", err=True)
            sys.exit(1)

        # Step 2: Trim
        profile_cfg = cfg.get("profiles", {}).get(profile, {})
        ext = profile_cfg.get("extension", profile_cfg.get("codec", "mp3"))
        output_name = f"ringtone_{os.path.basename(url)}_{int(s)}-{int(e)}.{ext}"
        output_path = os.path.join(_exports_dir(), output_name)

        trimmed = trim(audio_path, s, e)

        # Step 3: Apply effects
        trimmed = apply_all(
            trimmed,
            do_normalize=cfg.get("normalize", True),
            do_fade=cfg.get("fade", True),
            do_bass=profile_cfg.get("bass_boost", False),
            normalize_db=profile_cfg.get("normalize_db", -1.0),
            fade_ms=profile_cfg.get("fade_ms", 200),
        )

        # Step 4: Export
        export_fmt = profile_cfg.get("codec", "mp3")
        if export_fmt == "aac":
            export_fmt = "mp4"
        trimmed.export(output_path, format=export_fmt,
                       bitrate=profile_cfg.get("bitrate", "192k"))

        click.echo(f"Exported: {output_path}")

    elif mode == "heatmap":
        from analyzer.heatmap import fetch_heatmap, get_peak_segment

        meta = ytdl.get_metadata(url)
        real_vid = meta.get("video_id") if meta else None

        # Fetch heatmap data using the real YouTube video ID
        markers = fetch_heatmap(real_vid) if real_vid else None
        if markers is None:
            click.echo(
                "Heatmap data is not available for this video. "
                "Try '--mode auto' instead.",
                err=True,
            )
            sys.exit(1)

        # Resolve duration
        if duration is None:
            duration = cfg.get("default_duration", 30)

        # Find the best segment
        profile_cfg = cfg.get("profiles", {}).get(profile, {})
        total_dur = meta.get("duration") if meta else None

        best = get_peak_segment(markers, duration=duration, max_end=total_dur)
        if best is None:
            click.echo("Could not find a suitable segment from heatmap.", err=True)
            sys.exit(1)

        s, e = best["start"], best["end"]
        click.echo(f"Heatmap peak: {s:.1f}s to {e:.1f}s "
                   f"(avg intensity: {best['avg_intensity']:.2f})")

        # Trim
        ext = profile_cfg.get("extension", profile_cfg.get("codec", "mp3"))
        output_name = f"ringtone_heatmap_{real_vid}_{int(s)}-{int(e)}.{ext}"
        output_path = os.path.join(_exports_dir(), output_name)

        trimmed = trim(audio_path, s, e)

        # Apply effects
        trimmed = apply_all(
            trimmed,
            do_normalize=cfg.get("normalize", True),
            do_fade=cfg.get("fade", True),
            do_bass=profile_cfg.get("bass_boost", False),
            normalize_db=profile_cfg.get("normalize_db", -1.0),
            fade_ms=profile_cfg.get("fade_ms", 200),
        )

        export_fmt = profile_cfg.get("codec", "mp3")
        if export_fmt == "aac":
            export_fmt = "mp4"
        trimmed.export(output_path, format=export_fmt,
                       bitrate=profile_cfg.get("bitrate", "192k"))
        click.echo(f"Exported: {output_path}")

    elif mode == "notification":
        # notification mode: find short punchy segment (3-8s)
        from analyzer.heatmap import fetch_heatmap
        from analyzer.scorer import compute_scores, find_nearest_beat, find_phrase_end
        from analyzer.beat import get_beat_times

        meta = ytdl.get_metadata(url)
        real_vid = meta.get("video_id") if meta else None
        heatmap_markers = fetch_heatmap(real_vid) if real_vid else None
        total_dur = meta.get("duration") if meta else None

        candidates = compute_scores(
            audio_path,
            duration=duration or 5,
            heatmap_markers=heatmap_markers,
            max_end=total_dur,
        )
        if not candidates:
            click.echo("Could not identify a good notification segment.", err=True)
            sys.exit(1)

        best = candidates[0]
        s, e = best["start"], best["end"]
        beat_times = get_beat_times(audio_path)
        smart_s = find_nearest_beat(beat_times, s)
        smart_e = find_phrase_end(beat_times, e)

        click.echo(f"Notification segment: {smart_s:.1f}s - {smart_e:.1f}s")
        profile_cfg = cfg.get("profiles", {}).get(profile, {})
        ext = profile_cfg.get("extension", profile_cfg.get("codec", "mp3"))
        output_name = f"notification_{vid}_{int(smart_s)}-{int(smart_e)}.{ext}"
        output_path = os.path.join(_exports_dir(), output_name)

        trimmed = trim(audio_path, smart_s, smart_e)
        trimmed = apply_all(
            trimmed,
            do_normalize=True,
            do_fade=True,
            do_bass=True,
            normalize_db=-2.0,
            fade_ms=100,
        )
        export_fmt = profile_cfg.get("codec", "mp3")
        if export_fmt == "aac":
            export_fmt = "mp4"
        trimmed.export(output_path, format=export_fmt,
                       bitrate=profile_cfg.get("bitrate", "192k"))
        click.echo(f"Exported notification: {output_path}")

    else:  # auto mode - run full scoring pipeline
        from analyzer.heatmap import fetch_heatmap
        from analyzer.scorer import compute_scores
        from analyzer.beat import get_beat_times

        meta = ytdl.get_metadata(url)
        real_vid = meta.get("video_id") if meta else None

        # Try to get heatmap data using the real YouTube video ID
        heatmap_markers = fetch_heatmap(real_vid) if real_vid else None

        # Resolve duration
        if duration is None:
            duration = cfg.get("default_duration", 30)

        total_dur = meta.get("duration") if meta else None

        # Run the unified scoring engine
        log = get_logger()
        log.info("Running full scoring pipeline for %s", url)
        candidates = compute_scores(
            audio_path,
            duration=duration,
            heatmap_markers=heatmap_markers,
            max_end=total_dur,
        )

        if not candidates:
            click.echo("Could not identify any good segment.", err=True)
            sys.exit(1)

        # Display top 5
        click.echo("")
        click.echo("Top Candidate Segments:")
        click.echo("-" * 60)
        for c in candidates:
            dur = c["end"] - c["start"]
            labels_str = ", ".join(c.get("labels", []))
            click.echo(
                f"  #{c['rank']} {c['rank_name']:25s} "
                f"{c['start']:7.1f}s - {c['end']:7.1f}s "
                f"({dur:.0f}s)  Score: {c['final_score']:5.1f}  "
                f"[{labels_str}]"
            )
        click.echo("-" * 60)

        # Auto-select #1 and export
        best = candidates[0]
        s, e = best["start"], best["end"]

        # Smart start/end
        beat_times = get_beat_times(audio_path)
        from analyzer.scorer import find_nearest_beat, find_phrase_end
        smart_s = find_nearest_beat(beat_times, s)
        smart_e = find_phrase_end(beat_times, e)
        if smart_s != s or smart_e != e:
            click.echo(f"Snapped to: {smart_s:.1f}s - {smart_e:.1f}s "
                       f"(beat-aligned)")

        profile_cfg = cfg.get("profiles", {}).get(profile, {})
        ext = profile_cfg.get("extension", profile_cfg.get("codec", "mp3"))
        output_name = f"ringtone_auto_{real_vid}_{int(smart_s)}-{int(smart_e)}.{ext}"
        output_path = os.path.join(_exports_dir(), output_name)

        trimmed = trim(audio_path, smart_s, smart_e)
        trimmed = apply_all(
            trimmed,
            do_normalize=cfg.get("normalize", True),
            do_fade=cfg.get("fade", True),
            do_bass=profile_cfg.get("bass_boost", False),
            normalize_db=profile_cfg.get("normalize_db", -1.0),
            fade_ms=profile_cfg.get("fade_ms", 200),
        )

        export_fmt = profile_cfg.get("codec", "mp3")
        if export_fmt == "aac":
            export_fmt = "mp4"
        trimmed.export(output_path, format=export_fmt,
                       bitrate=profile_cfg.get("bitrate", "192k"))
        click.echo(f"Exported: {output_path}")


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------

@main.command()
@_url_arg
@_start_opt
@_duration_opt
def preview(url, start, duration):
    """
    Preview a segment by playing it through the system audio.

    Requires the 'playsound' library or a system audio player.
    """
    audio_path = ytdl.download(url)

    if start is None:
        start = 0.0
    if duration is None:
        duration = 10.0

    end = start + duration

    trimmed = trim(audio_path, start, end)
    temp_path = os.path.join(_exports_dir(), "_preview.wav")
    trimmed.export(temp_path, format="wav")

    click.echo(f"Range: {start}s to {end}s ({duration}s)")

    # Show ASCII waveform
    try:
        wf = extract_waveform(audio_path, num_points=60)
        ascii_art = ascii_waveform(wf, width=60, height=5)
        click.echo("")
        click.echo(ascii_art)
        click.echo("")
    except Exception as exc:
        log = get_logger()
        log.debug("Could not render waveform: %s", exc)

    click.echo("Playing...")

    # Try a few playback methods
    try:
        import subprocess
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-hide_banner", temp_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            import playsound
            playsound.playsound(temp_path)
        except ImportError:
            click.echo(
                "No audio player found. Install ffplay (part of FFmpeg) "
                "or the 'playsound' Python package."
            )
            sys.exit(1)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@main.command()
@click.argument("input_path")
@click.argument("profile_name", type=click.Choice(
    ["android", "iphone", "notification", "alarm", "tiktok"]))
@click.option("--start", type=float, help="Start time in seconds")
@click.option("--duration", type=float, help="Duration in seconds")
def export(input_path, profile_name, start, duration):
    """
    Convert an existing audio file per an export profile.

    INPUT_PATH: path to an audio file (WAV, MP3, etc.)
    PROFILE_NAME: android, iphone, notification, alarm, or tiktok
    """
    from pydub import AudioSegment
    cfg = load_config()
    profile = cfg.get("profiles", {}).get(profile_name, {})

    audio = AudioSegment.from_file(input_path)

    # Trim if requested
    if start is not None:
        s_ms = int(start * 1000)
        if duration is not None:
            e_ms = s_ms + int(duration * 1000)
        else:
            e_ms = len(audio)
        audio = audio[s_ms:e_ms]

    # Apply profile effects
    audio = apply_all(
        audio,
        do_normalize=True,
        do_fade=True,
        do_bass=profile.get("bass_boost", False),
        normalize_db=profile.get("normalize_db", -1.0),
        fade_ms=profile.get("fade_ms", 200),
    )

    # Determine output extension
    ext = profile.get("extension", profile.get("codec", "mp3"))
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(_exports_dir(), f"{base}_{profile_name}.{ext}")

    codec = profile.get("codec", "mp3")
    bitrate = profile.get("bitrate", "192k")

    audio.export(output_path, format=codec, bitrate=bitrate)
    click.echo(f"Exported: {output_path}")


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------

@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["manual", "heatmap", "auto", "notification"]),
              default="auto", help="Selection mode")
@click.option("--profile", type=click.Choice(
    ["android", "iphone", "notification", "alarm", "tiktok"]),
    default=None, help="Export profile")
@click.option("--duration", type=float, default=None, help="Segment duration in seconds")
@click.option("--limit", type=int, default=None, help="Max number of URLs to process")
def batch(input_file, mode, profile, duration, limit):
    """
    Process multiple YouTube URLs from a text file.

    INPUT_FILE: path to a text file with one YouTube URL per line.
    Blank lines and comments (lines starting with #) are ignored.
    """
    cfg = load_config()
    if profile is None:
        profile = cfg.get("default_profile", "android")

    # Read URLs from file
    urls = []
    with open(input_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)

    if limit:
        urls = urls[:limit]

    if not urls:
        click.echo("No URLs found in the file.", err=True)
        sys.exit(1)

    click.echo(f"Processing {len(urls)} URLs in batch mode ({mode}/{profile})...")
    click.echo("")

    log = get_logger()
    success = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        click.echo(f"[{i}/{len(urls)}] {url}")
        try:
            # Generate each URL
            audio_path = ytdl.download(url)

            if mode == "manual":
                click.echo("  Skipping (manual mode requires start/end).")
                continue

            from analyzer.heatmap import fetch_heatmap
            from analyzer.scorer import compute_scores, find_nearest_beat, find_phrase_end
            from analyzer.beat import get_beat_times

            meta = ytdl.get_metadata(url)
            real_vid = meta.get("video_id") if meta else None
            heatmap_markers = fetch_heatmap(real_vid) if real_vid else None
            total_dur = meta.get("duration") if meta else None

            candidates = compute_scores(
                audio_path,
                duration=duration or cfg.get("default_duration", 30),
                heatmap_markers=heatmap_markers,
                max_end=total_dur,
            )

            if not candidates:
                click.echo("  No candidates found.")
                failed += 1
                continue

            best = candidates[0]
            s, e = best["start"], best["end"]
            beat_times = get_beat_times(audio_path)
            smart_s = find_nearest_beat(beat_times, s)
            smart_e = find_phrase_end(beat_times, e)

            profile_cfg = cfg.get("profiles", {}).get(profile, {})
            ext = profile_cfg.get("extension", profile_cfg.get("codec", "mp3"))
            seg_dur = int(smart_e - smart_s)
            output_name = f"batch_{i:03d}_{vid}_{int(smart_s)}-{int(smart_e)}_{seg_dur}s.{ext}"
            output_path = os.path.join(_exports_dir(), output_name)

            trimmed = trim(audio_path, smart_s, smart_e)
            trimmed = apply_all(
                trimmed,
                do_normalize=cfg.get("normalize", True),
                do_fade=cfg.get("fade", True),
                do_bass=profile_cfg.get("bass_boost", False),
                normalize_db=profile_cfg.get("normalize_db", -1.0),
                fade_ms=profile_cfg.get("fade_ms", 200),
            )
            trimmed.export(output_path, format=profile_cfg.get("codec", "mp3"),
                           bitrate=profile_cfg.get("bitrate", "192k"))

            click.echo(f"  Exported: {output_path}")
            success += 1

        except Exception as e:
            log.error("Failed to process %s: %s", url, e)
            click.echo(f"  FAILED: {e}")
            failed += 1

    click.echo("")
    click.echo(f"Batch complete: {success} succeeded, {failed} failed.")


# ---------------------------------------------------------------------------
# gui
# ---------------------------------------------------------------------------

@main.command()
def gui():
    """Launch the desktop GUI."""
    try:
        from ui.main_window import launch
        launch()
    except ImportError as e:
        click.echo(
            "GUI dependencies not installed. Run: uv add ringforge[gui]",
            err=True,
        )
        click.echo(f"Import error: {e}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
