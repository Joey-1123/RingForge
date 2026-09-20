# ringforge Optimization

## Core Problem
`generate` loads audio via `librosa.load()` **4+ times** and spawns **2 yt-dlp subprocesses**. Fix: share data, not reload.

## Tasks

### 1. SignalContext — single audio load
Create `analyzer/_context.py` that loads audio once and shares arrays. All analyzers read from it instead of loading independently.
- `compute_scores()`, `get_beat_times()`, all analyzers use shared context
- **Files**: `analyzer/_context.py`, `analyzer/scorer.py`, `analyzer/energy.py`, `analyzer/beat.py`, `analyzer/repetition.py`, `app/cli.py`

### 2. Merge yt-dlp calls
`generate` calls `download()` then `get_metadata()` — two subprocesses. Merge into one.
- **Files**: `downloader/ytdl.py`, `app/cli.py`

### 3. Algorithm fixes
- `get_peak_segment()`: O(n²) → O(n) prefix-sum sliding window
- `compute_scores()`: pre-compute cumulative arrays, replace per-step loops with O(1) window sums
- **Files**: `analyzer/heatmap.py`, `analyzer/scorer.py`

### 4. Batch parallelism
ProcessPoolExecutor for batch mode. **File**: `app/cli.py`

## Result
- `generate`: 4+ audio loads → 1, 2 yt-dlp calls → 1
- Expected: 30s+ → <10s for a 5-min video
