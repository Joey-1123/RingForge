"""
Custom QWidget for rendering audio waveforms.

Displays the full-waveform RMS profile with highlighted candidate segments
and the currently selected segment in a different color.
"""

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget


# Color scheme
COLOR_BG = QColor("#1e1e2e")
COLOR_WAVEFORM = QColor("#89b4fa")
COLOR_WAVEFORM_FILL = QColor(137, 180, 250, 80)
COLOR_CANDIDATE = QColor("#a6e3a1")
COLOR_CANDIDATE_FILL = QColor(166, 227, 161, 60)
COLOR_SELECTED = QColor("#f9e2af")
COLOR_SELECTED_FILL = QColor(249, 226, 175, 80)
COLOR_TEXT = QColor("#cdd6f4")
COLOR_GRID = QColor("#313244")
COLOR_CURSOR = QColor("#f38ba8")


class WaveformWidget(QWidget):
    """Interactive waveform display with candidate segment highlights."""

    segment_clicked = Signal(int)  # candidate index
    position_changed = Signal(float)  # seconds (when user clicks to seek)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMouseTracking(True)

        # Data
        self._samples = []          # waveform RMS values (0-1)
        self._duration = 0.0        # total audio duration in seconds
        self._candidates = []       # list of candidate dicts with start/end
        self._selected_index = -1   # which candidate is selected
        self._play_position = -1.0  # current playback cursor in seconds
        self._hover_time = -1.0     # mouse hover position in seconds

    def set_waveform(self, samples: list[float], duration: float):
        """Set the waveform data to display."""
        self._samples = samples
        self._duration = duration
        self.update()

    def set_candidates(self, candidates: list[dict]):
        """Set the list of candidate segments to highlight."""
        self._candidates = candidates
        self.update()

    def set_selected_index(self, index: int):
        """Highlight a specific candidate as selected."""
        self._selected_index = index
        self.update()

    def set_play_position(self, seconds: float):
        """Update the playback cursor position."""
        self._play_position = seconds
        self.update()

    def clear_play_position(self):
        """Remove the playback cursor."""
        self._play_position = -1.0
        self.update()

    def _time_to_x(self, time_sec: float) -> float:
        """Convert time in seconds to x coordinate."""
        if self._duration <= 0:
            return 0
        margin = 40  # left/right margin
        w = self.width() - 2 * margin
        return margin + (time_sec / self._duration) * w

    def _x_to_time(self, x: float) -> float:
        """Convert x coordinate to time in seconds."""
        if self._duration <= 0:
            return 0
        margin = 40
        w = self.width() - 2 * margin
        if w <= 0:
            return 0
        return ((x - margin) / w) * self._duration

    def paintEvent(self, event):
        """Render the waveform."""
        if not self._samples:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 40
        plot_w = w - 2 * margin
        plot_h = h - 30
        baseline_y = 15 + plot_h

        # Background
        painter.fillRect(0, 0, w, h, COLOR_BG)

        # Time axis labels
        painter.setPen(COLOR_TEXT)
        font = QFont("monospace", 8)
        painter.setFont(font)
        num_labels = max(2, int(self._duration / 30))
        for i in range(num_labels + 1):
            t = (i / num_labels) * self._duration
            x = self._time_to_x(t)
            mins, secs = divmod(int(t), 60)
            painter.drawText(QRectF(x - 20, h - 15, 40, 12),
                             Qt.AlignmentFlag.AlignCenter,
                             f"{mins}:{secs:02d}")

        # Draw candidate segment backgrounds
        for i, cand in enumerate(self._candidates):
            sx = self._time_to_x(cand["start"])
            ex = self._time_to_x(cand["end"])
            rect = QRectF(sx, 15, ex - sx, plot_h)

            if i == self._selected_index:
                painter.fillRect(rect, COLOR_SELECTED_FILL)
                painter.setPen(QPen(COLOR_SELECTED, 2))
                painter.drawRect(rect)
            else:
                painter.fillRect(rect, COLOR_CANDIDATE_FILL)
                painter.setPen(QPen(COLOR_CANDIDATE, 1))
                painter.drawRect(rect)

        # Draw waveform fill
        painter.setPen(QPen(COLOR_WAVEFORM, 1))
        num_points = len(self._samples)
        if num_points > 1:
            path = []
            for i in range(num_points):
                x = margin + (i / (num_points - 1)) * plot_w
                val = self._samples[i]
                y = baseline_y - val * plot_h * 0.9
                path.append((x, y))

            # Draw filled waveform
            fill_path = painter.clipRegion()
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                painter.setPen(QPen(COLOR_WAVEFORM, 1.5))
                painter.drawLine(x1, y1, x2, y2)

        # Draw play cursor
        if self._play_position >= 0:
            cx = self._time_to_x(self._play_position)
            painter.setPen(QPen(COLOR_CURSOR, 2))
            painter.drawLine(cx, 10, cx, baseline_y)

        # Draw hover indicator
        if self._hover_time >= 0:
            hx = self._time_to_x(self._hover_time)
            painter.setPen(QPen(QColor("#f5c2e7"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(hx, 10, hx, baseline_y)
            mins, secs = divmod(int(self._hover_time), 60)
            text = f"{mins}:{secs:02d}"
            painter.setPen(COLOR_TEXT)
            painter.drawText(QRectF(hx - 20, 0, 40, 12),
                             Qt.AlignmentFlag.AlignCenter, text)

        painter.end()

    def mousePressEvent(self, event):
        """Handle mouse click to select segment or seek."""
        t = self._x_to_time(event.position().x())
        if t < 0 or t > self._duration:
            return

        # Check if click is inside a candidate segment
        for i, cand in enumerate(self._candidates):
            if cand["start"] <= t <= cand["end"]:
                self._selected_index = i
                self.segment_clicked.emit(i)
                self.update()
                return

        # If not on a segment, treat as seek
        self.position_changed.emit(t)

    def mouseMoveEvent(self, event):
        """Track mouse position for hover indicator."""
        t = self._x_to_time(event.position().x())
        if 0 <= t <= self._duration:
            self._hover_time = t
            self.update()

    def leaveEvent(self, event):
        """Clear hover indicator when mouse leaves."""
        self._hover_time = -1.0
        self.update()
