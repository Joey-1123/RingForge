from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap
from PySide6.QtWidgets import QWidget

COLOR_BG = QColor("#1e1e2e")
COLOR_WAVEFORM = QColor("#89b4fa")
COLOR_CANDIDATE = QColor("#a6e3a1")
COLOR_CANDIDATE_FILL = QColor(166, 227, 161, 60)
COLOR_SELECTED = QColor("#f9e2af")
COLOR_SELECTED_FILL = QColor(249, 226, 175, 80)
COLOR_TEXT = QColor("#cdd6f4")
COLOR_CURSOR = QColor("#f38ba8")
COLOR_HANDLE = QColor("#f9e2af")
HANDLE_WIDTH = 8


class WaveformWidget(QWidget):
    segment_clicked = Signal(int)
    position_changed = Signal(float)
    candidate_modified = Signal(int, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMouseTracking(True)

        self._samples = []
        self._duration = 0.0
        self._candidates = []
        self._selected_index = -1
        self._play_position = -1.0
        self._hover_time = -1.0

        self._cache = QPixmap()
        self._cache_dirty = True
        self._drag_handle = None
        self._drag_start_time = 0.0

    def set_waveform(self, samples: list[float], duration: float):
        self._samples = samples
        self._duration = duration
        self._cache_dirty = True
        self.update()

    def set_candidates(self, candidates: list[dict]):
        self._candidates = candidates
        self._cache_dirty = True
        self.update()

    def set_selected_index(self, index: int):
        self._selected_index = index
        self._cache_dirty = True
        self.update()

    def set_play_position(self, seconds: float):
        self._play_position = seconds
        self.update()

    def clear_play_position(self):
        self._play_position = -1.0
        self.update()

    def resizeEvent(self, event):
        self._cache_dirty = True
        super().resizeEvent(event)

    def _time_to_x(self, time_sec: float) -> float:
        if self._duration <= 0:
            return 0
        margin = 40
        w = self.width() - 2 * margin
        return margin + (time_sec / self._duration) * w

    def _x_to_time(self, x: float) -> float:
        if self._duration <= 0:
            return 0
        margin = 40
        w = self.width() - 2 * margin
        if w <= 0:
            return 0
        return ((x - margin) / w) * self._duration

    def _handle_rect(self, x: float) -> QRectF:
        return QRectF(x - HANDLE_WIDTH / 2, 15, HANDLE_WIDTH, self.height() - 45)

    def _render_cache(self):
        if not self._samples or self._duration <= 0:
            self._cache = QPixmap()
            return

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        self._cache = QPixmap(w, h)
        self._cache.fill(COLOR_BG)

        painter = QPainter(self._cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 40
        plot_w = w - 2 * margin
        plot_h = h - 30
        baseline_y = 15 + plot_h

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

        for i, cand in enumerate(self._candidates):
            sx = self._time_to_x(cand["start"])
            ex = self._time_to_x(cand["end"])
            rect = QRectF(sx, 15, ex - sx, plot_h)

            if i == self._selected_index:
                painter.fillRect(rect, COLOR_SELECTED_FILL)
                painter.setPen(QPen(COLOR_SELECTED, 2))
                painter.drawRect(rect)

                hx1 = self._time_to_x(cand["start"])
                hx2 = self._time_to_x(cand["end"])
                handle_top = QPointF(hx1, 15)
                handle_bot = QPointF(hx1, 15 + plot_h)
                painter.setPen(QPen(COLOR_HANDLE, 1))
                painter.setBrush(COLOR_HANDLE)
                painter.drawRect(QRectF(hx1 - HANDLE_WIDTH / 2, 15, HANDLE_WIDTH, plot_h).adjusted(0, 0, 0, -1))
                painter.drawRect(QRectF(hx2 - HANDLE_WIDTH / 2, 15, HANDLE_WIDTH, plot_h).adjusted(0, 0, 0, -1))
            else:
                painter.fillRect(rect, COLOR_CANDIDATE_FILL)
                painter.setPen(QPen(COLOR_CANDIDATE, 1))
                painter.drawRect(rect)

        painter.setPen(QPen(COLOR_WAVEFORM, 1))
        num_points = len(self._samples)
        if num_points > 1:
            for i in range(num_points - 1):
                x1 = margin + (i / (num_points - 1)) * plot_w
                x2 = margin + ((i + 1) / (num_points - 1)) * plot_w
                y1 = baseline_y - self._samples[i] * plot_h * 0.9
                y2 = baseline_y - self._samples[i + 1] * plot_h * 0.9
                painter.drawLine(x1, y1, x2, y2)

        painter.end()
        self._cache_dirty = False

    def paintEvent(self, event):
        if not self._samples:
            return

        if self._cache_dirty:
            self._render_cache()

        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)

        w = self.width()
        h = self.height()
        margin = 40
        plot_h = h - 30
        baseline_y = 15 + plot_h

        if self._play_position >= 0:
            cx = self._time_to_x(self._play_position)
            painter.setPen(QPen(COLOR_CURSOR, 2))
            painter.drawLine(cx, 10, cx, baseline_y)

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

    def _hit_test_handle(self, x: float) -> str | None:
        if self._selected_index < 0 or self._selected_index >= len(self._candidates):
            return None
        cand = self._candidates[self._selected_index]
        sx = self._time_to_x(cand["start"])
        ex = self._time_to_x(cand["end"])
        if abs(x - sx) <= HANDLE_WIDTH:
            return "start"
        if abs(x - ex) <= HANDLE_WIDTH:
            return "end"
        return None

    def mousePressEvent(self, event):
        t = self._x_to_time(event.position().x())
        if t < 0 or t > self._duration:
            return

        handle = self._hit_test_handle(event.position().x())
        if handle:
            self._drag_handle = handle
            self._drag_start_time = t
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            return

        for i, cand in enumerate(self._candidates):
            if cand["start"] <= t <= cand["end"]:
                self._selected_index = i
                self._cache_dirty = True
                self.segment_clicked.emit(i)
                self.update()
                return

        self.position_changed.emit(t)

    def mouseMoveEvent(self, event):
        t = self._x_to_time(event.position().x())
        if t < 0 or t > self._duration:
            return

        if self._drag_handle:
            cand = self._candidates[self._selected_index]
            if self._drag_handle == "start":
                new_start = max(0.0, min(t, cand["end"] - 2.0))
                cand["start"] = new_start
            else:
                new_end = min(self._duration, max(t, cand["start"] + 2.0))
                cand["end"] = new_end
            self._cache_dirty = True
            self.update()
            return

        self._hover_time = t
        handle = self._hit_test_handle(event.position().x())
        self.setCursor(Qt.CursorShape.SizeHorCursor if handle else Qt.CursorShape.ArrowCursor)
        self.update()

    def mouseReleaseEvent(self, event):
        if self._drag_handle:
            cand = self._candidates[self._selected_index]
            self.candidate_modified.emit(self._selected_index, cand["start"], cand["end"])
            self._drag_handle = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, event):
        self._hover_time = -1.0
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
