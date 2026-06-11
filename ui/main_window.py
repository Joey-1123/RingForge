"""
Main application window for RingForge GUI.

Combines URL input, waveform display, candidate selection, playback,
and export into a single desktop interface.
"""

import os
import sys

from PySide6.QtCore import Qt, QTimer, Signal, QSettings, QThread
from PySide6.QtGui import QFont, QIcon, QColor, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QListWidget,
    QListWidgetItem, QSplitter, QStatusBar, QMessageBox, QFrame,
    QProgressBar, QSlider, QFileDialog, QTabWidget, QDoubleSpinBox,
    QDialog, QGroupBox, QFormLayout,
)

from core.logging import get_logger, setup as setup_logging
from core.config import load as load_config
from core.waveform import extract_waveform
from downloader import ytdl
from audio.trim import trim
from audio.effects import apply_all
from audio.export import export_profile, get_supported_profiles
from ui.waveform_widget import WaveformWidget
from ui.player import AudioPlayer
from ui.worker import AnalysisWorker

log = get_logger()


class BatchDialog(QDialog):
    """Queue-based batch processing dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Process")
        self.setMinimumSize(500, 400)
        self._items = []
        self._worker = None
        self._thread = None
        self._cancelled = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        input_row = QHBoxLayout()
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("YouTube URL or file path...")
        self._add_btn = QPushButton("Add")
        self._add_btn.clicked.connect(self._on_add)
        input_row.addWidget(self._input_edit, 1)
        input_row.addWidget(self._add_btn)
        layout.addLayout(input_row)

        self._list = QListWidget()
        layout.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._on_remove)
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._on_clear)
        self._process_btn = QPushButton("Process All")
        self._process_btn.clicked.connect(self._on_process)
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.close)
        btn_row.addWidget(self._remove_btn)
        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._process_btn)
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

    def _on_add(self):
        text = self._input_edit.text().strip()
        if text:
            self._items.append((text, "pending"))
            self._list.addItem(f"[...] {text}")
            self._input_edit.clear()

    def _on_remove(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._items):
            self._items.pop(row)
            self._list.takeItem(row)

    def _on_clear(self):
        self._items.clear()
        self._list.clear()

    def _on_process(self):
        if not self._items:
            return
        self._cancelled = False
        self._process_btn.setText("Cancel")
        self._process_btn.clicked.disconnect()
        self._process_btn.clicked.connect(self.cancel)
        self._add_btn.setEnabled(False)
        self._remove_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._input_edit.setEnabled(False)
        self._close_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setMaximum(len(self._items))
        self._progress.setValue(0)
        self._process_next(0)

    def _process_next(self, index):
        if self._cancelled or index >= len(self._items):
            self._finish_batch()
            return

        item_text = self._items[index][0]
        self._items[index] = (item_text, "processing")
        self._list.item(index).setText(f"[...] {item_text}")
        self._progress.setValue(index)

        self._thread = QThread(self)
        self._worker = AnalysisWorker(item_text)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(
            lambda path, wf, cands, idx=index: self._on_item_done(idx, path, wf, cands)
        )
        self._worker.error_occurred.connect(
            lambda err, idx=index: self._on_item_error(idx, err)
        )
        self._worker.finished.connect(self._thread.quit)
        self._worker.error_occurred.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_item_done(self, index, audio_path, waveform, candidates):
        try:
            if not candidates:
                raise ValueError("No candidates found")
            cand = candidates[0]
            audio = trim(
                audio_path,
                cand["start"],
                cand["end"],
            )
            export_profile(
                audio,
                "android",
                base_name=f"batch_{int(cand['start'])}-{int(cand['end'])}",
            )
            self._items[index] = (self._items[index][0], "done")
            self._list.item(index).setText(f"[OK]   {self._items[index][0]}")
        except Exception:
            self._items[index] = (self._items[index][0], "failed")
            self._list.item(index).setText(f"[FAIL] {self._items[index][0]}")
        self._process_next(index + 1)

    def _on_item_error(self, index, error_msg):
        self._items[index] = (self._items[index][0], "failed")
        self._list.item(index).setText(f"[FAIL] {self._items[index][0]}")
        self._process_next(index + 1)

    def _finish_batch(self):
        self._progress.setValue(len(self._items) if not self._cancelled else 0)
        self._progress.setVisible(False)
        self._process_btn.setText("Process All")
        self._process_btn.clicked.disconnect()
        self._process_btn.clicked.connect(self._on_process)
        self._add_btn.setEnabled(True)
        self._remove_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        self._input_edit.setEnabled(True)
        self._close_btn.setEnabled(True)
        done = sum(1 for _, s in self._items if s == "done")
        failed = sum(1 for _, s in self._items if s == "failed")
        QMessageBox.information(
            self, "Batch Complete",
            f"Processed {done + failed} items: {done} OK, {failed} failed",
        )

    def cancel(self):
        self._cancelled = True
        if self._worker:
            self._worker.cancel()
        if self._thread:
            self._thread.quit()
            self._thread.wait()


class RingForgeWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RingForge")
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)

        # State
        self._audio_path = None
        self._candidates = []
        self._selected_idx = -1
        self._playing_preview = False
        self._preview_path = None
        self._settings = QSettings("RingForge", "RingForge")
        self._worker = None
        self._thread = None

        # Initialize UI
        self._init_ui()
        self._init_player()
        self._connect_signals()
        self._init_shortcuts()
        self._restore_settings()

    def _init_ui(self):
        """Set up all UI widgets."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # ---- Top bar: URL input + action buttons ----
        top_bar = QHBoxLayout()

        self._open_btn = QPushButton("Open File")
        self._open_btn.clicked.connect(self._on_open_file)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText(
            "YouTube URL or local file path (drag & drop supported)..."
        )
        self._url_input.returnPressed.connect(self._on_download)

        self._download_btn = QPushButton("Analyze")
        self._download_btn.clicked.connect(self._on_download)

        self._batch_btn = QPushButton("Batch")
        self._batch_btn.clicked.connect(self._on_open_batch)

        top_bar.addWidget(self._open_btn)
        top_bar.addWidget(self._url_input, 1)
        top_bar.addWidget(self._download_btn)
        top_bar.addWidget(self._batch_btn)
        main_layout.addLayout(top_bar)

        # ---- Progress bar ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximum(0)
        main_layout.addWidget(self._progress)

        # ---- Main splitter: waveform + right panel ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: waveform + playback controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._waveform = WaveformWidget()
        self._waveform.segment_clicked.connect(self._on_segment_clicked)
        self._waveform.position_changed.connect(self._on_waveform_seek)
        self._waveform.candidate_modified.connect(self._on_candidate_modified)

        controls = QHBoxLayout()
        self._play_btn = QPushButton("Play")
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self._on_play_pause)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(70)
        self._volume_slider.setFixedWidth(120)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        self._volume_label = QLabel("70%")

        self._time_label = QLabel("0:00 / 0:00")

        controls.addWidget(self._play_btn)
        controls.addWidget(self._stop_btn)
        controls.addStretch()
        controls.addWidget(self._volume_label)
        controls.addWidget(self._volume_slider)
        controls.addStretch()
        controls.addWidget(self._time_label)

        left_layout.addWidget(self._waveform, 1)
        left_layout.addLayout(controls)
        splitter.addWidget(left_widget)

        # ---- Right panel: tabbed ----
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._right_tabs = QTabWidget()

        # --- Tab 1: Candidates ---
        candidates_tab = QWidget()
        candidates_layout = QVBoxLayout(candidates_tab)

        candidate_label = QLabel("Top Candidates")
        candidate_label.setFont(QFont("sans-serif", 12, QFont.Weight.Bold))
        candidates_layout.addWidget(candidate_label)

        self._candidate_list = QListWidget()
        self._candidate_list.currentRowChanged.connect(self._on_candidate_selected)
        candidates_layout.addWidget(self._candidate_list, 1)

        export_frame = QFrame()
        export_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        export_layout = QVBoxLayout(export_frame)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        self._profile_combo = QComboBox()
        for p in get_supported_profiles():
            self._profile_combo.addItem(p.capitalize(), p)
        profile_row.addWidget(self._profile_combo, 1)
        export_layout.addLayout(profile_row)

        self._export_btn = QPushButton("Export Selected")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        export_layout.addWidget(self._export_btn)

        self._open_exports_btn = QPushButton("Open Exports Folder")
        self._open_exports_btn.clicked.connect(self._on_open_exports)
        export_layout.addWidget(self._open_exports_btn)

        candidates_layout.addWidget(export_frame)
        self._right_tabs.addTab(candidates_tab, "Candidates")

        # --- Tab 2: Manual ---
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)

        manual_label = QLabel("Manual Mode")
        manual_label.setFont(QFont("sans-serif", 12, QFont.Weight.Bold))
        manual_layout.addWidget(manual_label)

        manual_group = QGroupBox("Segment Range")
        manual_form = QFormLayout(manual_group)

        self._manual_start = QDoubleSpinBox()
        self._manual_start.setRange(0, 999999)
        self._manual_start.setDecimals(1)
        self._manual_start.setSuffix("s")
        self._manual_start.setValue(0)
        manual_form.addRow("Start:", self._manual_start)

        self._manual_end = QDoubleSpinBox()
        self._manual_end.setRange(0, 999999)
        self._manual_end.setDecimals(1)
        self._manual_end.setSuffix("s")
        self._manual_end.setValue(30)
        manual_form.addRow("End:", self._manual_end)

        manual_layout.addWidget(manual_group)

        manual_btn_row = QHBoxLayout()
        self._manual_preview_btn = QPushButton("Preview")
        self._manual_preview_btn.setEnabled(False)
        self._manual_preview_btn.clicked.connect(self._on_manual_preview)
        manual_btn_row.addWidget(self._manual_preview_btn)

        self._manual_export_btn = QPushButton("Export As...")
        self._manual_export_btn.setEnabled(False)
        self._manual_export_btn.clicked.connect(self._on_manual_export)
        manual_btn_row.addWidget(self._manual_export_btn)

        manual_layout.addLayout(manual_btn_row)
        manual_layout.addStretch()
        self._right_tabs.addTab(manual_tab, "Manual")

        right_layout.addWidget(self._right_tabs)
        right_widget.setLayout(right_layout)
        right_widget.setMinimumWidth(300)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, 1)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    def _init_player(self):
        """Set up the audio player and position timer."""
        self._player = AudioPlayer(self)
        self._player.playback_finished.connect(self._on_playback_finished)
        self._player.error_occurred.connect(self._on_player_error)
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(100)
        self._position_timer.timeout.connect(self._update_playback_ui)

    def _connect_signals(self):
        """(unused) cross-thread signals connected per-worker."""

    def _init_shortcuts(self):
        """Set up keyboard shortcuts."""
        QShortcut(QKeySequence("Space"), self, self._on_play_pause)
        QShortcut(QKeySequence("Escape"), self, self._on_stop)
        QShortcut(QKeySequence("Ctrl+E"), self, self._on_export)
        QShortcut(QKeySequence("Ctrl+O"), self, self._on_open_file)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self._on_manual_export)

    def _restore_settings(self):
        """Restore window geometry and saved values."""
        geo = self._settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        url = self._settings.value("last_url", "")
        self._url_input.setText(url)
        vol = int(self._settings.value("volume", 70))
        self._volume_slider.setValue(vol)
        profile = self._settings.value("profile", "android")
        idx = self._profile_combo.findData(profile)
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)

    def _save_settings(self):
        """Persist window geometry and current state."""
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("last_url", self._url_input.text())
        self._settings.setValue("volume", self._volume_slider.value())
        self._settings.setValue("profile", self._profile_combo.currentData())

    def closeEvent(self, event):
        """Save settings on close."""
        self._save_settings()
        super().closeEvent(event)

    # ---- Actions ----

    def dragEnterEvent(self, event):
        """Accept drag events with file URLs or text."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle file drops."""
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if path:
                self._url_input.setText(path)
                self._on_download()
        elif event.mimeData().hasText():
            self._url_input.setText(event.mimeData().text().strip())
            self._on_download()

    def _on_open_file(self):
        """Open a file dialog to select an audio file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a *.aac *.wma);;All Files (*)",
        )
        if path:
            self._url_input.setText(path)
            self._on_download()

    def _on_open_exports(self):
        """Open the exports folder in the file manager."""
        exports_dir = os.path.join(os.path.dirname(__file__), "..", "exports")
        os.makedirs(exports_dir, exist_ok=True)
        if sys.platform == "linux":
            import subprocess
            subprocess.run(
                ["xdg-open", exports_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def _on_open_batch(self):
        """Open the batch processing dialog."""
        dialog = BatchDialog(self)
        dialog.show()

    def _on_download(self):
        """Start analysis in a background QThread."""
        input = self._url_input.text().strip()
        if not input:
            return

        self._progress.setVisible(True)
        self._download_btn.setEnabled(False)
        self._status.showMessage("Analyzing...")
        self._candidate_list.clear()
        self._candidates = []
        self._selected_idx = -1
        self._waveform.set_candidates([])
        self._waveform.clear_play_position()
        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._manual_preview_btn.setEnabled(False)
        self._manual_export_btn.setEnabled(False)

        if self._worker:
            self._worker.cancel()
        if self._thread:
            self._thread.quit()
            self._thread.wait()

        self._thread = QThread(self)
        self._worker = AnalysisWorker(input)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_download_complete)
        self._worker.error_occurred.connect(self._on_download_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error_occurred.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_download_complete(self, audio_path, waveform_data, candidates):
        """Update UI after download and analysis complete."""
        self._audio_path = audio_path
        self._candidates = candidates
        self._progress.setVisible(False)
        self._download_btn.setEnabled(True)

        dur = waveform_data.get("duration", 0)
        self._waveform.set_waveform(
            waveform_data.get("samples", []),
            dur,
        )

        self._candidate_list.clear()
        for i, c in enumerate(candidates):
            labels = ", ".join(c.get("labels", []))
            cdur = c["end"] - c["start"]
            label = (
                f"#{c.get('rank', i+1)} {c.get('rank_name', 'Candidate')}\n"
                f"  {c['start']:.1f}s - {c['end']:.1f}s ({cdur:.0f}s)\n"
                f"  Score: {c['final_score']:.1f}  [{labels}]"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._candidate_list.addItem(item)

        self._waveform.set_candidates(candidates)

        # Update manual tab with audio duration
        self._manual_start.setMaximum(dur)
        self._manual_end.setMaximum(dur)
        self._manual_end.setValue(min(dur, 30))
        self._manual_preview_btn.setEnabled(True)
        self._manual_export_btn.setEnabled(True)

        self._status.showMessage(
            f"Loaded {dur:.0f}s audio with {len(candidates)} candidates"
        )

    def _on_download_error(self, error_msg):
        """Show error message."""
        self._progress.setVisible(False)
        self._download_btn.setEnabled(True)
        QMessageBox.critical(self, "Download Error", error_msg)
        self._status.showMessage("Error")

    def _on_candidate_selected(self, row):
        """Highlight the selected candidate on the waveform."""
        if row < 0 or row >= len(self._candidates):
            return
        self._selected_idx = row
        self._waveform.set_selected_index(row)
        self._export_btn.setEnabled(True)

        c = self._candidates[row]
        mins1, secs1 = divmod(int(c["start"]), 60)
        mins2, secs2 = divmod(int(c["end"]), 60)
        self._time_label.setText(f"{mins1}:{secs1:02d} / {mins2}:{secs2:02d}")

        # Sync manual tab
        self._manual_start.setValue(c["start"])
        self._manual_end.setValue(c["end"])

        self._preview_segment(c["start"], c["end"])

    def _on_segment_clicked(self, index):
        """Handle click on waveform candidate."""
        self._candidate_list.setCurrentRow(index)

    def _on_candidate_modified(self, index, new_start, new_end):
        """Handle snap-drag of candidate edge on waveform."""
        if 0 <= index < len(self._candidates):
            self._candidates[index]["start"] = new_start
            self._candidates[index]["end"] = new_end
            self._status.showMessage(
                f"Candidate #{index+1}: {new_start:.1f}s - {new_end:.1f}s"
            )
            self._manual_start.setValue(new_start)
            self._manual_end.setValue(new_end)

    def _on_waveform_seek(self, seconds):
        """Handle click on waveform for seeking."""
        if self._player and self._preview_path:
            self._player.seek(seconds)

    def _preview_segment(self, start, end):
        """Trim, save temp, and load into player for preview."""
        if not self._audio_path:
            return

        self._player.stop()
        self._position_timer.stop()

        trimmed = trim(self._audio_path, start, end)
        preview_dir = os.path.join(os.path.dirname(__file__), "..", "exports")
        os.makedirs(preview_dir, exist_ok=True)
        self._preview_path = os.path.join(preview_dir, "_preview.wav")
        trimmed.export(self._preview_path, format="wav")

        self._player.load(self._preview_path)
        self._play_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)
        self._play_btn.setText("Play")
        self._playing_preview = False

    def _on_manual_preview(self):
        """Preview the custom segment from manual tab."""
        start = self._manual_start.value()
        end = self._manual_end.value()
        if end <= start:
            QMessageBox.warning(self, "Invalid Range", "End must be after start.")
            return
        self._preview_segment(start, end)
        self._status.showMessage(f"Previewing {start:.1f}s - {end:.1f}s")

    def _on_manual_export(self):
        """Export the manual segment with Save As dialog."""
        start = self._manual_start.value()
        end = self._manual_end.value()
        if end <= start:
            QMessageBox.warning(self, "Invalid Range", "End must be after start.")
            return
        if not self._audio_path:
            return
        self._export_segment(start, end)

    def _on_play_pause(self):
        """Toggle play/pause."""
        if not self._preview_path:
            return

        if self._playing_preview:
            self._player.pause()
            self._play_btn.setText("Play")
            self._position_timer.stop()
        else:
            self._player.play()
            self._play_btn.setText("Pause")
            self._position_timer.start()
        self._playing_preview = not self._playing_preview

    def _on_stop(self):
        """Stop playback and reset."""
        self._player.stop()
        self._play_btn.setText("Play")
        self._playing_preview = False
        self._position_timer.stop()
        self._waveform.clear_play_position()

    def _on_playback_finished(self):
        """Reset UI when playback ends."""
        self._play_btn.setText("Play")
        self._playing_preview = False
        self._position_timer.stop()
        self._waveform.clear_play_position()

    def _on_player_error(self, error_msg):
        """Handle player errors."""
        log.error("Playback error: %s", error_msg)
        QMessageBox.warning(self, "Playback Error", error_msg)
        self._on_playback_finished()

    def _on_volume_changed(self, value):
        """Update volume from slider."""
        vol = value / 100.0
        self._player.set_volume(vol)
        self._volume_label.setText(f"{value}%")

    def _update_playback_ui(self):
        """Update time label and waveform cursor during playback."""
        pos = self._player.position
        dur = self._player.duration

        mins1, secs1 = divmod(int(pos), 60)
        mins2, secs2 = divmod(int(dur), 60)
        self._time_label.setText(f"{mins1}:{secs1:02d} / {mins2}:{secs2:02d}")

        self._waveform.set_play_position(pos)

    def _export_segment(self, start, end):
        """Trim, show Save As dialog, and export a segment."""
        profile_name = self._profile_combo.currentData()
        cfg = load_config()
        profile = cfg.get("profiles", {}).get(profile_name, {})
        ext = profile.get("extension", profile.get("codec", "mp3"))

        default_name = f"ringforge_{int(start)}-{int(end)}_{profile_name}.{ext}"
        exports_dir = os.path.join(os.path.dirname(__file__), "..", "exports")
        os.makedirs(exports_dir, exist_ok=True)
        default_path = os.path.join(exports_dir, default_name)

        path, _ = QFileDialog.getSaveFileName(
            self, "Export As", default_path,
            f"Audio Files (*.{ext});;All Files (*)",
        )
        if not path:
            return

        try:
            audio = trim(self._audio_path, start, end)

            processed = apply_all(
                audio,
                do_normalize=True,
                do_fade=True,
                do_bass=profile.get("bass_boost", False),
                normalize_db=profile.get("normalize_db", -1.0),
                fade_ms=profile.get("fade_ms", 200),
            )

            codec = profile.get("codec", "mp3")
            export_format = codec
            if codec == "aac":
                export_format = "mp4"
            bitrate = profile.get("bitrate", "192k")

            processed.export(
                path,
                format=export_format,
                bitrate=bitrate,
                parameters=["-write_xing", "0"] if codec == "mp3" else [],
            )
            self._status.showMessage(f"Exported: {path}")
        except Exception as e:
            log.error("Export failed: %s", e)
            QMessageBox.critical(self, "Export Error", str(e))

    def _on_export(self):
        """Export the selected candidate with Save As dialog."""
        if self._selected_idx < 0 or not self._candidates:
            return
        cand = self._candidates[self._selected_idx]
        self._export_segment(cand["start"], cand["end"])


def launch():
    """Launch the RingForge GUI application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from PySide6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e2e"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#181825"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#313244"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#89b4fa"))
    app.setPalette(palette)

    window = RingForgeWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
