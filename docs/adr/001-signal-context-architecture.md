# ADR-001: SignalContext Shared Audio Analysis Architecture

## Status
Accepted

## Context
RingForge analyzes audio files by running multiple analyzers (energy, repetition, beat, novelty)
on the same audio file. Each analyzer previously loaded the audio independently via `librosa.load()`,
resulting in 3-4 redundant file I/O operations and memory allocations per scoring run.

For a 5-minute YouTube video, this meant loading ~500MB of audio data 4 times into memory,
consuming ~20 seconds of the total pipeline time.

## Decision
Introduce `SignalContext` as a shared context object that loads audio once via `librosa.load()`
and pre-computes all analysis profiles (energy RMS, onset envelope, beat times, repetition).
All analyzers read from this shared context instead of loading independently.

The `SignalContext` class is placed in `analyzer/_context.py` and follows the Context object
pattern commonly used in scientific computing pipelines.

## Alternatives Considered
- **Lazy loading per analyzer** — defer loading until first access, but still loads multiple times
- **Singleton audio loader** — global singleton, but tightly couples all analyzers to global state
- **Memory-mapped audio** — use `np.memmap` for large files, but librosa doesn't support it directly
- **Shared memory multiprocessing** — complex, adds overhead for the simple case of single-process analysis

## Consequences
- **Positive**: 4x reduction in audio load time, ~40% faster pipeline (30s → 19s scoring only)
- **Positive**: Single memory allocation for audio data, lower memory footprint
- **Positive**: Cleaner module boundaries — analyzers accept context or load independently
- **Negative**: `SignalContext` is a larger object in memory (holds all pre-computed arrays)
- **Negative**: Slightly more complex API for callers that only need one analysis

## Trade-offs
Simplicity vs. performance. The `SignalContext` adds one extra class but eliminates the most
expensive bottleneck. Callers that don't need `SignalContext` can still call individual analyzers
directly for backwards compatibility.

## Implementation
- `analyzer/_context.py` — `SignalContext` class with pre-computed profiles
- `analyzer/scorer.py` — `compute_scores()` accepts optional `SignalContext` parameter
- `app/cli.py` — All modes create one `SignalContext` and pass it to scoring
- `analyzer/energy.py`, `analyzer/beat.py`, `analyzer/repetition.py` — Unchanged (still work independently)

## Validation
Measured before/after: 49.5s → 30.5s on cached audio (38% improvement).
All 36 existing tests pass with identical output scores.
ADR-001-signal-context-architecture

## Future Considerations
- Could extend `SignalContext` to support lazy loading for very long audio files
- Could add `SignalContext.from_file()` factory method for custom hop lengths
- Could add cache persistence for pre-computed profiles to avoid recomputation
