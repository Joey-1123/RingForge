# Contributing to RingForge

## Setup

```bash
# Clone the repository
git clone https://github.com/Joey-1123/RingForge.git
cd RingForge

# Install dependencies (with optional extras)
uv sync                          # core
uv sync --extra youtube          # with YouTube download support
uv sync --extra gui              # with PySide6 GUI
uv sync --extra all              # everything
```

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=app --cov=analyzer --cov=core

# Lint
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy .

# Pre-commit hooks
pre-commit install
```

## Project Structure

```
app/         - CLI entry point (click commands)
analyzer/    - Signal analysis (energy, beat, repetition, heatmap, scoring)
audio/       - Audio processing (trim, effects, export)
core/        - Cache, config, logging, waveform
downloader/  - yt-dlp wrapper (YouTube download)
ui/          - PySide6 desktop GUI
tests/       - pytest test suite
docs/        - Documentation, ADRs, logo
config/      - Default configuration (config.toml)
```

## Adding a New Export Profile

1. Add a new section to `config/config.toml` under `[profiles]`
2. Define: `codec`, `bitrate`, `default_duration`, `fade_ms`, `normalize_db`, `bass_boost`, `mono`
3. Reference it in your CLI command with `--profile <name>`

## Adding a New Analyzer

1. Create a new file in `analyzer/` (e.g., `analyzer/tempo.py`)
2. Implement `compute_<name>_profile(path)` returning a numpy array
3. Integrate into `analyzer/scorer.py` via `compute_scores()`
4. Add tests in `tests/test_<name>.py`

## Code Style

- Python 3.12+ features are encouraged (type hints, pattern matching, etc.)
- Line length: 100 characters
- Use `ruff` for linting and `mypy` for type checking
- Follow existing naming conventions: `snake_case` for variables/functions, `PascalCase` for classes
- Document all public functions with docstrings

## Commit Convention

```
<type>: <description>

<optional body>

Co-authored-by: RingForge <contributor>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `build`, `ci`

## Reporting Issues

- **Bugs**: Open a GitHub issue with reproduction steps
- **Security**: Email **security@ringforge.dev** or use GitHub Security Advisories
- **Features**: Open a feature request issue with the proposal

## License

All Rights Reserved. See [LICENSE](LICENSE) for details.
