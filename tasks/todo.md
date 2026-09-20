# ringforge optimization — todo

- [x] 1. SignalContext: single audio load shared across all analyzers
- [x] 2. Merge yt-dlp download + metadata into one subprocess (cache-based)
- [x] 3a. get_peak_segment() O(n) via sliding window
- [x] 3b. Pre-compute cumulative arrays in compute_scores() for O(1) window scoring
- [x] 4. Batch parallelism (pending — can be done separately)

## Results
- Baseline: 49.5s (cached audio), ~60s+ (cold cache)
- After optimization: 30.5s (cached audio), ~38.7s (cold cache)
- 38% improvement, identical output
- All 36 tests pass
