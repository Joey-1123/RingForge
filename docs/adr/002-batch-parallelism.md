# ADR-002: Batch Parallelism via ProcessPoolExecutor

## Status
Accepted

## Context
The `batch` command processed URLs sequentially — one at a time. For a file with 10 URLs,
each taking ~30s to process, the total time was ~5 minutes. CPU cores sat idle during I/O waits.

The `ringforge` CLI runs as a single process, so batch mode was inherently serial.

## Decision
Refactor batch mode to use `concurrent.futures.ProcessPoolExecutor`. Each URL is processed
in a separate worker process, allowing true parallelism across all available CPU cores.

The per-URL processing logic is extracted into `_process_batch_url()` as a module-level function
so it can be pickled by the executor. Each worker creates its own `SignalContext`, ensuring
no shared state issues.

## Alternatives Considered
- **ThreadPoolExecutor** — Limited by GIL for CPU-bound librosa operations; not effective
- **asyncio** — librosa is not async-native; would require wrapping all calls
- **Multiprocessing.Pool** — Lower-level API, less flexible than ProcessPoolExecutor
- **Ray/Dask** — Overkill for a CLI tool; adds dependency overhead
- **Subprocess per URL** — Manual process management, less ergonomic than executor

## Consequences
- **Positive**: Near-linear speedup with CPU cores (8 URLs on 4 cores → ~2x speedup)
- **Positive**: Each worker is isolated — failures don't crash the entire batch
- **Positive**: Simple API — no external dependencies added
- **Negative**: Higher memory usage (each worker loads its own copy of librosa + audio)
- **Negative**: ProcessPoolExecutor has startup overhead (~100ms per worker)
- **Negative**: Workers cannot share cached data; each downloads audio independently

## Trade-offs
Memory vs. speed. For batch jobs with many URLs, the speedup justifies the extra memory.
For small batches (< 4 URLs), sequential may be comparable. The `max_workers` parameter
defaults to `min(os.cpu_count(), len(urls))` to avoid over-provisioning.

## Implementation
- `app/cli.py` — `_process_batch_url()` function + `ProcessPoolExecutor` in `batch` command
- Workers are stateless — each creates its own `SignalContext` and audio pipeline
- Failure isolation via try/except in worker, reported back to main process

## Future Considerations
- Could add a shared cache (SQLite or Redis) for workers to avoid redundant downloads
- Could add progress reporting via a callback or queue
- Could support `--workers` CLI flag for user control
