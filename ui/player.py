"""
Simple audio playback wrapper using QMediaPlayer.

Handles loading, playing, pausing, and seeking audio files.
"""

from PySide6.QtCore import QUrl, Signal, QObject
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class AudioPlayer(QObject):
    """Wrapper around QMediaPlayer for simple audio playback."""

    position_changed = Signal(float)  # seconds
    duration_changed = Signal(float)  # seconds
    playback_finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.errorOccurred.connect(self._on_error)

    def load(self, file_path: str):
        """Load an audio file for playback."""
        self._player.setSource(QUrl.fromLocalFile(file_path))

    def play(self):
        """Start or resume playback."""
        self._player.play()

    def pause(self):
        """Pause playback."""
        self._player.pause()

    def stop(self):
        """Stop playback and reset position."""
        self._player.stop()

    def seek(self, seconds: float):
        """Seek to a position in seconds."""
        self._player.setPosition(int(seconds * 1000))

    def set_volume(self, volume: float):
        """Set volume from 0.0 to 1.0."""
        self._audio_output.setVolume(volume)

    @property
    def position(self) -> float:
        """Current playback position in seconds."""
        return self._player.position() / 1000.0

    @property
    def duration(self) -> float:
        """Total duration of loaded audio in seconds."""
        return self._player.duration() / 1000.0

    @property
    def is_playing(self) -> bool:
        """Whether audio is currently playing."""
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def _on_error(self, error, error_string):
        self.error_occurred.emit(error_string)
