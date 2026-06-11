import os
import traceback

from PySide6.QtCore import QObject, Signal

from core.config import load as load_config
from core.logging import get_logger
from core.waveform import extract_waveform

log = get_logger()


class AnalysisWorker(QObject):
    finished = Signal(str, object, object)
    error_occurred = Signal(str)

    def __init__(self, input: str, duration: int | None = None, parent=None):
        super().__init__(parent)
        self._input = input
        cfg = load_config()
        self._duration = duration or cfg.get("default_duration", 30)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            is_local = os.path.isfile(self._input)
            heatmap_markers = None
            total_dur = None

            if is_local:
                audio_path = self._input
            else:
                from downloader import ytdl
                audio_path = ytdl.download(self._input)
                if self._cancelled:
                    return
                from analyzer.heatmap import fetch_heatmap
                meta = ytdl.get_metadata(self._input)
                real_vid = meta.get("video_id") if meta else None
                heatmap_markers = fetch_heatmap(real_vid) if real_vid else None
                total_dur = meta.get("duration") if meta else None

            if self._cancelled:
                return

            wf = extract_waveform(audio_path, num_points=500)

            if self._cancelled:
                return

            from analyzer.scorer import compute_scores
            candidates = compute_scores(
                audio_path,
                duration=self._duration,
                heatmap_markers=heatmap_markers,
                max_end=total_dur,
            )

            if not self._cancelled:
                self.finished.emit(audio_path, wf, candidates)
        except Exception as e:
            log.error("Analysis failed: %s", e)
            traceback.print_exc()
            if not self._cancelled:
                self.error_occurred.emit(str(e))
