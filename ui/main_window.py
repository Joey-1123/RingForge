"""
Main application window for RingForge GUI.

Combines URL input, waveform display, candidate selection, playback,
and export into a single desktop interface.
"""

import os
import sys
import threading

from PySide6.QtCore import Qt, QTimer, Signal, QSettings
from PySide6.QtGui import QFont, QIcon, QColor, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QListWidget,
    QListWidgetItem, QSplitter, QStatusBar, QMessageBox, QFrame,
    QProgressBar, QSlider, QFileDialog,
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

log = get_logger()


class RingForgeWindow(QMainWindow):
    """Main application window."""

    # Signals for cross-thread communication
    download_complete = Signal(str, object, object)
    download_error = Signal(str)

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

        top_bar.addWidget(self._open_btn)
        top_bar.addWidget(self._url_input, 1)
        top_bar.addWidget(self._download_btn)
        main_layout.addLayout(top_bar)

        # ---- Progress bar ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximum(0)  # indeterminate
        main_layout.addWidget(self._progress)

        # ---- Main splitter: waveform + candidates ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: waveform
        left_panel = QVBoxLayout()

        self._waveform = WaveformWidget()
        self._waveform.segment_clicked.connect(self._on_segment_clicked)
        self._waveform.position_changed.connect(self._on_waveform_seek)

        # Playback controls below waveform
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

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._waveform, 1)
        left_layout.addLayout(controls)
        splitter.addWidget(left_widget)

        # Right side: candidate list + export
        right_panel = QVBoxLayout()

        candidate_label = QLabel("Top Candidates")
        candidate_label.setFont(QFont("sans-serif", 12, QFont.Weight.Bold))
        right_panel.addWidget(candidate_label)

        self._candidate_list = QListWidget()
        self._candidate_list.currentRowChanged.connect(self._on_candidate_selected)
        right_panel.addWidget(self._candidate_list, 1)

        # Export controls
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

        right_panel.addWidget(export_frame)

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
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

        # Timer to poll position
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(100)  # 100ms
        self._position_timer.timeout.connect(self._update_playback_ui)

    def _connect_signals(self):
        """Connect cross-thread signals to their handlers."""
        self.download_complete.connect(self._on_download_complete)
        self.download_error.connect(self._on_download_error)

    def _init_shortcuts(self):
        """Set up keyboard shortcuts."""
        QShortcut(QKeySequence("Space"), self, self._on_play_pause)
        QShortcut(QKeySequence("Escape"), self, self._on_stop)
        QShortcut(QKeySequence("Ctrl+E"), self, self._on_export)
        QShortcut(QKeySequence("Ctrl+O"), self, self._on_open_file)

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

    def _on_download(self):
        """Start downloading the URL in a background thread."""
        url = self._url_input.text().strip()
        if not url:
            return

        self._progress.setVisible(True)
        self._download_btn.setEnabled(False)
        self._status.showMessage("Downloading...")
        self._candidate_list.clear()
        self._candidates = []
        self._selected_idx = -1
        self._waveform.set_candidates([])
        self._waveform.clear_play_position()
        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)
        self._export_btn.setEnabled(False)

        # Download in background thread
        thread = threading.Thread(target=self._download_worker, args=(url,), daemon=True)
        thread.start()

    def _download_worker(self, input):
        """Download audio and process in background."""
        try:
            is_local = os.path.isfile(input)

            if is_local:
                audio_path = input
                heatmap_markers = None
                total_dur = None
            else:
                audio_path = ytdl.download(input)
                from analyzer.heatmap import fetch_heatmap
                meta = ytdl.get_metadata(input)
                real_vid = meta.get("video_id") if meta else None
                heatmap_markers = fetch_heatmap(real_vid) if real_vid else None
                total_dur = meta.get("duration") if meta else None

            # Extract waveform
            wf = extract_waveform(audio_path, num_points=500)

            # Run scorer
            from analyzer.scorer import compute_scores

            candidates = compute_scores(
                audio_path,
                duration=30,
                heatmap_markers=heatmap_markers,
                max_end=total_dur,
            )

            # Emit signal to update UI on main thread
            self.download_complete.emit(audio_path, wf, candidates)
        except Exception as e:
            log.error("Download failed: %s", e)
            self.download_error.emit(str(e))

    def _on_download_complete(self, audio_path, waveform_data, candidates):
        """Update UI after download and analysis complete."""
        self._audio_path = audio_path
        self._candidates = candidates
        self._progress.setVisible(False)
        self._download_btn.setEnabled(True)

        # Update waveform
        self._waveform.set_waveform(
            waveform_data.get("samples", []),
            waveform_data.get("duration", 0),
        )

        # Update candidate list
        self._candidate_list.clear()
        for i, c in enumerate(candidates):
            labels = ", ".join(c.get("labels", []))
            dur = c["end"] - c["start"]
            label = (
                f"#{c.get('rank', i+1)} {c.get('rank_name', 'Candidate')}\n"
                f"  {c['start']:.1f}s - {c['end']:.1f}s ({dur:.0f}s)\n"
                f"  Score: {c['final_score']:.1f}  [{labels}]"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._candidate_list.addItem(item)

        # Highlight candidates on waveform
        self._waveform.set_candidates(candidates)

        self._status.showMessage(
            f"Loaded {waveform_data.get('duration', 0):.0f}s audio with "
            f"{len(candidates)} candidates"
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

        # Update time label to show candidate duration
        c = self._candidates[row]
        mins1, secs1 = divmod(int(c["start"]), 60)
        mins2, secs2 = divmod(int(c["end"]), 60)
        self._time_label.setText(f"{mins1}:{secs1:02d} / {mins2}:{secs2:02d}")

        # Preview the segment
        self._preview_segment(c["start"], c["end"])

    def _on_segment_clicked(self, index):
        """Handle click on waveform candidate."""
        self._candidate_list.setCurrentRow(index)

    def _on_waveform_seek(self, seconds):
        """Handle click on waveform for seeking."""
        if self._player and self._preview_path:
            self._player.seek(seconds)

    def _preview_segment(self, start, end):
        """Trim, save temp, and load into player for preview."""
        if not self._audio_path:
            return

        # Stop current playback
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

    def _on_export(self):
        """Export the selected candidate using the chosen profile."""
        if self._selected_idx < 0 or not self._candidates:
            return

        cand = self._candidates[self._selected_idx]
        profile_name = self._profile_combo.currentData()

        if not self._audio_path:
            return

        try:
            # Trim the segment
            audio = trim(self._audio_path, cand["start"], cand["end"])

            # Export per profile
            output_path = export_profile(
                audio,
                profile_name,
                base_name=f"ringforge_{int(cand['start'])}-{int(cand['end'])}",
            )
            self._status.showMessage(f"Exported: {output_path}")
        except Exception as e:
            log.error("Export failed: %s", e)
            QMessageBox.critical(self, "Export Error", str(e))


def launch():
    """Launch the RingForge GUI application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Apply dark palette
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
