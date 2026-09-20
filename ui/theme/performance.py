"""
Performance optimization utilities for RingForge UI.

Provides dirty-region rendering, LRU caching,
progressive rendering, and performance monitoring.
"""

import time
import tracemalloc
from collections import OrderedDict
from functools import lru_cache
from PySide6.QtCore import QTimer, QElapsedTimer, Qt, QRect, QRectF
from PySide6.QtWidgets import QWidget

from core.tokens import ANIM_FAST, ANIM_NORMAL, get_reduced_motion

# ═══════════════════════════════════════════════════════════════
# LRU CACHE for rendered waveform segments
# ═══════════════════════════════════════════════════════════════

class LRUCache:
    """Fixed-capacity LRU cache for rendered QPixmap segments."""

    def __init__(self, max_size: int = 10):
        self._max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key):
        """Get cached value by key. Returns None if miss."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, key, value):
        """Put a value into the cache, evicting oldest if at capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self):
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def hit_rate(self) -> float:
        """Return cache hit rate as a percentage."""
        total = self._hits + self._misses
        return (self._hits / total * 100) if total > 0 else 0.0

    @property
    def size(self) -> int:
        return len(self._cache)


# ═══════════════════════════════════════════════════════════════
# Dirty Region Rendering — only re-render changed areas
# ═══════════════════════════════════════════════════════════════

class DirtyRegionRenderer:
    """Tracks dirty regions and batches re-renders.

    Instead of re-rendering the entire waveform on every update,
    only re-render the regions that actually changed.
    """

    def __init__(self):
        self._dirty_rects: list[QRect] = []
        self._full_dirty = True
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(ANIM_FAST)  # 150ms batch window
        self._pending_callback = None

    def mark_dirty(self, rect: QRect = None):
        """Mark a region as dirty. If None, marks entire area."""
        if rect is None:
            self._full_dirty = True
            self._dirty_rects.clear()
        else:
            self._dirty_rects.append(rect)

    def mark_full(self):
        """Mark entire area as needing full re-render."""
        self._full_dirty = True
        self._dirty_rects.clear()

    def schedule_render(self, callback):
        """Schedule a batched render callback.

        All marks within ANIM_FAST ms will be batched into one render.
        """
        self._pending_callback = callback
        if not self._render_timer.isActive():
            self._render_timer.start()

    def flush(self) -> tuple[list[QRect], bool]:
        """Get all dirty regions and reset state. Returns (rects, full)."""
        rects = self._dirty_rects.copy()
        full = self._full_dirty
        self._dirty_rects.clear()
        self._full_dirty = False
        return rects, full

    def clear(self):
        self._dirty_rects.clear()
        self._full_dirty = False
        self._render_timer.stop()


# ═══════════════════════════════════════════════════════════════
# Progressive Rendering — show rough then refine
# ═══════════════════════════════════════════════════════════════

class ProgressiveRenderer:
    """Render waveform in stages: rough → refined → complete.

    Shows a low-resolution preview immediately, then refines
    on idle time to achieve smooth perceived performance.
    """

    def __init__(self, widget: QWidget, render_callback, quality_levels: int = 3):
        self._widget = widget
        self._render_callback = render_callback
        self._quality_levels = quality_levels
        self._current_level = 0
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(ANIM_FAST)
        self._timer.timeout.connect(self._next_level)

    def start(self):
        """Start progressive rendering from level 0."""
        self._current_level = 0
        self._render_level(0)

    def _render_level(self, level: int):
        """Render at a specific quality level."""
        self._render_callback(level, self._quality_levels)
        if level < self._quality_levels - 1:
            self._timer.start()

    def _next_level(self):
        """Advance to next quality level."""
        self._current_level += 1
        if self._current_level < self._quality_levels:
            self._render_level(self._current_level)
        else:
            self._current_level = self._quality_levels - 1

    @property
    def current_level(self) -> int:
        return self._current_level


# ═══════════════════════════════════════════════════════════════
# Performance Monitor — QElapsedTimer based profiling
# ═══════════════════════════════════════════════════════════════

class PerformanceMonitor:
    """Track frame times and detect performance issues."""

    def __init__(self, target_fps: int = 60, budget_ms: float = 16.0):
        self._target_fps = target_fps
        self._budget_ms = budget_ms
        self._timer = QElapsedTimer()
        self._frame_times: list[float] = []
        self._max_samples = 120
        self._dropped_frames = 0

    def frame_start(self):
        """Mark the start of a frame."""
        self._timer.restart()

    def frame_end(self) -> float:
        """Mark the end of a frame. Returns frame time in ms."""
        ms = self._timer.elapsed()
        self._frame_times.append(ms)
        if len(self._frame_times) > self._max_samples:
            self._frame_times.pop(0)
        if ms > self._budget_ms * 2:
            self._dropped_frames += 1
        return ms

    @property
    def avg_frame_time(self) -> float:
        """Average frame time in ms over recent samples."""
        if not self._frame_times:
            return 0.0
        return sum(self._frame_times) / len(self._frame_times)

    @property
    def current_fps(self) -> float:
        """Current estimated FPS."""
        avg = self.avg_frame_time
        return 1000.0 / avg if avg > 0 else 0.0

    @property
    def dropped_frames(self) -> int:
        return self._dropped_frames

    @property
    def is_healthy(self) -> bool:
        """Check if performance is within budget."""
        return self.avg_frame_time <= self._budget_ms

    def summary(self) -> dict:
        """Return performance summary dict."""
        return {
            "avg_frame_ms": round(self.avg_frame_time, 2),
            "current_fps": round(self.current_fps, 1),
            "target_fps": self._target_fps,
            "dropped_frames": self._dropped_frames,
            "healthy": self.is_healthy,
            "cache_hit_rate": 0,  # Updated by LRUCache
        }


# ═══════════════════════════════════════════════════════════════
# Memory Profiler
# ═══════════════════════════════════════════════════════════════

def profile_memory(label: str = "") -> dict:
    """Profile current memory usage using tracemalloc."""
    tracemalloc.start()
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics("lineno")[:5]
    tracemalloc.stop()

    total = sum(stat.size for stat in top_stats)
    return {
        "label": label,
        "total_mb": round(total / 1024 / 1024, 2),
        "top_allocations": [
            {"file": str(stat.traceback[0]), "size_kb": round(stat.size / 1024, 1)}
            for stat in top_stats
        ],
    }


# ═══════════════════════════════════════════════════════════════
# Undo Manager — wraps QUndoStack for waveform edits
# ═══════════════════════════════════════════════════════════════

class UndoManager:
    """Manages undo/redo for waveform segment edits.

    Uses a simple command pattern with QUndoStack integration.
    """

    def __init__(self, max_steps: int = 50):
        self._max_steps = max_steps
        self._stack: list[dict] = []
        self._index = -1

    def execute(self, command: dict):
        """Execute a command and push to stack.

        command dict must have: 'action', 'data', 'undo_data'
        """
        # Trim any redo history after current position
        self._stack = self._stack[:self._index + 1]
        self._stack.append(command)
        if len(self._stack) > self._max_steps:
            self._stack.pop(0)
            self._index -= 1
        self._index += 1

    def undo(self) -> dict | None:
        """Return the last command's undo data."""
        if self._index >= 0:
            cmd = self._stack[self._index]
            self._index -= 1
            return cmd.get("undo_data")
        return None

    def redo(self) -> dict | None:
        """Return the next command's data."""
        if self._index < len(self._stack) - 1:
            self._index += 1
            return self._stack[self._index]
        return None

    @property
    def can_undo(self) -> bool:
        return self._index >= 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._stack) - 1

    def clear(self):
        self._stack.clear()
        self._index = -1

    @property
    def size(self) -> int:
        return len(self._stack)
