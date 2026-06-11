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
ZOOM_MIN = 1.0
ZOOM_MAX = 50.0
ZOOM_STEP = 1.2


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
        self._panning = False
        self._pan_start_x = 0
        self._pan_start_offset = 0.0

        self._zoom = 1.0
        self._view_offset = 0.0

    def set_waveform(self, samples: list[float], duration: float):
        self._samples = samples
        self._duration = duration
        self._zoom = 1.0
        self._view_offset = 0.0
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

    def _vis_start(self) -> float:
        return self._view_offset

    def _vis_end(self) -> float:
        return min(self._view_offset + self._duration / self._zoom, self._duration)

    def _time_to_x(self, time_sec: float) -> float:
        if self._duration <= 0:
            return 0
        margin = 40
        w = self.width() - 2 * margin
        if w <= 0:
            return margin
        vs = self._vis_start()
        ve = self._vis_end()
        if ve <= vs:
            return margin
        return margin + ((time_sec - vs) / (ve - vs)) * w

    def _x_to_time(self, x: float) -> float:
        if self._duration <= 0:
            return 0
        margin = 40
        w = self.width() - 2 * margin
        if w <= 0:
            return 0
        vs = self._vis_start()
        ve = self._vis_end()
        if ve <= vs:
            return 0
        return vs + ((x - margin) / w) * (ve - vs)

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

        vs = self._vis_start()
        ve = self._vis_end()

        # Time labels
        painter.setPen(COLOR_TEXT)
        font = QFont("monospace", 8)
        painter.setFont(font)
        visible_range = ve - vs
        num_labels = max(2, int(visible_range / 15))
        for i in range(num_labels + 1):
            t = vs + (i / num_labels) * (ve - vs)
            if t < 0 or t > self._duration:
                continue
            x = self._time_to_x(t)
            mins, secs = divmod(int(t), 60)
            painter.drawText(QRectF(x - 20, h - 15, 40, 12),
                             Qt.AlignmentFlag.AlignCenter,
                             f"{mins}:{secs:02d}")

        # Candidates
        for i, cand in enumerate(self._candidates):
            # Skip candidates outside visible range
            if cand["end"] < vs or cand["start"] > ve:
                continue
            sx = self._time_to_x(cand["start"])
            ex = self._time_to_x(cand["end"])
            rect = QRectF(sx, 15, ex - sx, plot_h)

            if i == self._selected_index:
                painter.fillRect(rect, COLOR_SELECTED_FILL)
                painter.setPen(QPen(COLOR_SELECTED, 2))
                painter.drawRect(rect)

                hx1 = self._time_to_x(cand["start"])
                hx2 = self._time_to_x(cand["end"])
                painter.setPen(QPen(COLOR_HANDLE, 1))
                painter.setBrush(COLOR_HANDLE)
                painter.drawRect(QRectF(hx1 - HANDLE_WIDTH / 2, 15, HANDLE_WIDTH, plot_h).adjusted(0, 0, 0, -1))
                painter.drawRect(QRectF(hx2 - HANDLE_WIDTH / 2, 15, HANDLE_WIDTH, plot_h).adjusted(0, 0, 0, -1))
            else:
                painter.fillRect(rect, COLOR_CANDIDATE_FILL)
                painter.setPen(QPen(COLOR_CANDIDATE, 1))
                painter.drawRect(rect)

        # Waveform for visible range
        painter.setPen(QPen(COLOR_WAVEFORM, 1))
        num_points = len(self._samples)
        if num_points > 1:
            # Map visible range to sample indices
            first_idx = max(0, int((vs / self._duration) * num_points))
            last_idx = min(num_points - 1, int((ve / self._duration) * num_points))
            vis_points = last_idx - first_idx
            if vis_points > 0:
                for i in range(first_idx, last_idx):
                    t = (i / (num_points - 1)) * self._duration
                    x = self._time_to_x(t)
                    y = baseline_y - self._samples[i] * plot_h * 0.9
                    if i == first_idx:
                        prev_x = x
                        prev_y = y
                    painter.drawLine(prev_x, prev_y, x, y)
                    prev_x, prev_y = x, y

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
        baseline_y = 15 + h - 30

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

    def wheelEvent(self, event):
        if self._duration <= 0 or not self._samples:
            return

        t = self._x_to_time(event.position().x())
        t = max(0.0, min(t, self._duration))

        delta = event.angleDelta().y()
        factor = ZOOM_STEP if delta > 0 else 1.0 / ZOOM_STEP
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom * factor))
        if abs(new_zoom - self._zoom) < 0.01:
            return

        # Keep time under cursor fixed
        new_offset = t - (t - self._view_offset) * (self._zoom / new_zoom)
        self._view_offset = max(0.0, min(new_offset, self._duration - self._duration / new_zoom))
        self._zoom = new_zoom
        self._cache_dirty = True
        self.update()

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

        # Pan when zoomed in
        if self._zoom > 1.05:
            self._panning = True
            self._pan_start_x = event.position().x()
            self._pan_start_offset = self._view_offset
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
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

        if self._panning:
            dx = event.position().x() - self._pan_start_x
            vis_range = self._duration / self._zoom
            margin = 40
            plot_w = self.width() - 2 * margin
            if plot_w > 0:
                dt = -(dx / plot_w) * vis_range
                self._view_offset = max(0.0, min(
                    self._pan_start_offset + dt,
                    self._duration - vis_range,
                ))
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

        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, event):
        self._hover_time = -1.0
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
