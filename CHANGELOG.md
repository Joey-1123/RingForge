# Changelog

All notable changes to RingForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-20

### Added
- SignalContext pattern for single audio load (4x faster analysis)
- ProcessPoolExecutor for batch URL processing (parallel downloads)
- Cumulative sum arrays for O(1) window scoring
- O(n) sliding window for `get_peak_segment`
- Metadata caching to eliminate duplicate yt-dlp subprocess calls
- Full CI pipeline with GitHub Actions (`.github/workflows/ci.yml`)
- Pre-commit hooks configuration
- 36 pytest tests covering all modules
- 3 Architecture Decision Records (`docs/adr/`)
- YouTube download with `--js-runtimes node --no-update` flags
- Export profiles: Android, iPhone, Notification, Alarm, TikTok
- Desktop GUI with PySide6 (waveform, playback, manual editing)
- 5 export profiles with configurable audio effects

### Fixed
- `RingForce` → `RingForge` branding inconsistency in LICENSE and README
- "AI scoring engine" → "Signal scoring engine" in documentation
- `main.py` dead code stub removed
- `video_id` naming consistency (`real_vid` → `video_id`)
- SSRF prevention via URL host validation in `core/cache.py`
- Cache directory permissions set to `0o700`
- Logging output redirected to `stderr` to avoid stdout interleaving
- `SECURITY.md` updated with private disclosure channel
- Deprecated `video_id_from_url()` alias updated

### Security
- URL validation (`_validate_youtube_url`) restricts to youtube.com/youtu.be
- File path validation prevents path traversal attacks
- Cache directories created with restricted permissions (`0o700`)

### Changed
- Performance: 49.5s → 30.5s (38% improvement) for cached audio
- Performance: 38.7s for cold start (full pipeline with download)

## [0.1.0] - Initial Development

### Added
- Core audio analysis pipeline
- librosa-based energy, repetition, beat, and novelty scoring
- Top 5 candidate segment ranking
- Smart start/end beat alignment
- Sliding window candidate duration selection
- Cache-first processing strategy
- Local audio and YouTube URL input support
- PySide6 desktop GUI with waveform display
