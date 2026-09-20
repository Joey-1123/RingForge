# ADR-003: Module Interface Design

## Status
Accepted

## Context
RingForge's internal modules (`app`, `core`, `downloader`, `audio`, `analyzer`, `ui`)
have loose boundaries. Functions accept raw file paths instead of typed contracts,
and error handling is inconsistent across modules. The CLI layer directly imports
from analyzer modules, creating tight coupling.

## Decision
Establish clear module interfaces with typed contracts:

1. **Downloader interface**: `download(url) → str` and `get_metadata(url) → dict | None`
   - Consistent return types
   - Cache-aware — `get_metadata()` returns cached data without subprocess

2. **Analyzer interface**: `compute_scores(audio_path, context=None) → list[dict]`
   - Accepts optional `SignalContext` for shared analysis
   - Returns list of candidate dicts with consistent schema

3. **Audio interface**: `trim(path, start, end) → AudioSegment`, `export(audio, profile) → str`
   - Thin wrappers around pydub with consistent error handling

4. **Core interface**: `load_config() → dict`, `get_audio_path(id) → str`
   - Configuration and cache are the only shared state

5. **CLI interface**: All commands accept `click` arguments with consistent error handling

Each module has a public `__init__.py` that exports its public API, hiding internals.

## Alternatives Considered
- **Full REST API** — Overkill for a CLI tool; adds HTTP overhead and complexity
- **gRPC interfaces** — Too heavy for a single-process application
- **Message queue** — Unnecessary for sequential processing
- **Plugin system** — Premature optimization; modules are internal

## Consequences
- **Positive**: Clean module boundaries make testing easier
- **Positive**: `SignalContext` is the shared interface between downloader and analyzer
- **Positive**: `click` CLI provides consistent argument parsing and error messages
- **Negative**: Adding new modules requires updating `pyproject.toml` package list
- **Negative**: Type annotations add maintenance overhead

## Trade-offs
Flexibility vs. type safety. The project is a CLI tool, not a library. Type annotations
are added where they clarify the interface but not everywhere to avoid over-engineering.

## Implementation
- `analyzer/_context.py` — `SignalContext` shared interface
- `downloader/ytdl.py` — Clean `download()` and `get_metadata()` interface
- `app/cli.py` — Module-level `_process_batch_url()` for parallel execution
- `core/cache.py` — Stable cache interface with `save/load/exists` functions
- `pyproject.toml` — Added `ruff`, `mypy`, `pre-commit` dev dependencies

## Future Considerations
- Could add a `ringforge.api` module for programmatic usage
- Could add type stubs (`*.pyi`) for the public API
- Could add a plugin system for custom analyzers
