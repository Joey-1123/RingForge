"""
Empty state widgets for RingForge UI.

Shows placeholders when no audio is loaded, no candidates found,
or no batch items queued. Prevents blank screens and guides users.
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

from core.tokens import (
    BG_PRIMARY, BG_SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BRAND_PRIMARY, BRAND_ACCENT, BRAND_SUCCESS,
    BRAND_DANGER, FONT_SIZE_LARGE, FONT_SIZE_BASE, FONT_SIZE_SMALL,
    SPACING_XL, SPACING_LG, SPACING_MD, RADIUS_LG, TARGET_MIN_SIZE,
)


class EmptyState(QWidget):
    """Illustrated empty state with icon, title, description, and optional action.

    Usage:
        state = EmptyState(
            icon="🎵",  # or use Icon.from_name("audio")
            title="No Audio Loaded",
            description="Open a file or paste a YouTube URL to get started",
            button_text="Open File",
            button_callback=my_callback,
        )
    """

    def __init__(
        self,
        title: str = "No Audio Loaded",
        description: str = "Open a file or paste a YouTube URL to get started",
        button_text: str = "",
        button_callback=None,
        parent=None,
    ):
        super().__init__(parent)
        self._button_callback = button_callback
        self._setup_ui(title, description, button_text)

    def _setup_ui(self, title, description, button_text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL, SPACING_XL, SPACING_XL, SPACING_XL)
        layout.setSpacing(SPACING_MD)
        layout.addStretch(1)

        # Icon area
        icon_label = QLabel()
        icon_label.setText("🎵")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont(FONT_SIZE_2XL))
        icon_label.setFixedHeight(80)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont(FONT_SIZE_LARGE, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Description
        desc_label = QLabel(description)
        desc_label.setFont(QFont(FONT_SIZE_BASE))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Optional action button
        if button_text and self._button_callback:
            btn = QPushButton(button_text)
            btn.setMinimumSize(TARGET_MIN_SIZE, TARGET_MIN_SIZE)
            btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            btn.setAccessibleName(button_text)
            btn.clicked.connect(self._button_callback)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)
        self.setMinimumSize(300, 200)
        self.setObjectName("emptyState")

    def minimumSize(self):  # noqa: N802
        from PySide6.QtCore import QSize
        return QSize(300, 200)


class NoCandidatesEmpty(QWidget):
    """Empty state shown when analysis completes with no candidates."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL, SPACING_XL, SPACING_XL, SPACING_XL)
        layout.setSpacing(SPACING_MD)
        layout.addStretch(1)

        icon_label = QLabel()
        icon_label.setText("🔍")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont(FONT_SIZE_2XL))
        icon_label.setFixedHeight(80)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("No Candidates Found")
        title_label.setFont(QFont(FONT_SIZE_LARGE, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(
            "Try a different URL or adjust the scoring weights "
            "in Preferences to find better matches."
        )
        desc_label.setFont(QFont(FONT_SIZE_BASE))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)
        self.setMinimumSize(300, 200)


class NoBatchEmpty(QWidget):
    """Empty state shown when batch queue is empty."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL, SPACING_XL, SPACING_XL, SPACING_XL)
        layout.setSpacing(SPACING_MD)
        layout.addStretch(1)

        icon_label = QLabel()
        icon_label.setText("📋")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont(FONT_SIZE_2XL))
        icon_label.setFixedHeight(80)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("No Items in Queue")
        title_label.setFont(QFont(FONT_SIZE_LARGE, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(
            "Add YouTube URLs or file paths above to start batch processing."
        )
        desc_label.setFont(QFont(FONT_SIZE_BASE))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)
        self.setMinimumSize(300, 200)


class ErrorBanner(QWidget):
    """Inline error banner displayed in the status area.

    Shows a styled error message with an optional retry action.
    Automatically fades out after a timeout.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        from PySide6.QtWidgets import QHBoxLayout

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        self._icon_label = QLabel("⚠")
        self._icon_label.setStyleSheet(f"color: {BRAND_DANGER};")
        self._icon_label.setFont(QFont(FONT_SIZE_BASE, QFont.Weight.Bold))
        layout.addWidget(self._icon_label)

        self._message_label = QLabel()
        self._message_label.setFont(QFont(FONT_SIZE_BASE))
        self._message_label.setStyleSheet(f"color: {BRAND_DANGER};")
        self._message_label.setWordWrap(True)
        layout.addWidget(self._message_label, 1)

        self._retry_btn = QPushButton("Retry")
        self._retry_btn.setMinimumSize(64, 28)
        self._retry_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._retry_btn.setAccessibleName("Retry")
        self._retry_btn.clicked.connect(self._on_retry)
        layout.addWidget(self._retry_btn)

        self.setStyleSheet(
            f"""
            QWidget {{
                background: {BG_SECONDARY};
                border: 1px solid {BRAND_DANGER};
                border-radius: {RADIUS_LG}px;
                padding: {SPACING_SM}px {SPACING_MD}px;
            }}
            QPushButton {{
                background: {BRAND_DANGER};
                color: {BG_PRIMARY};
                border: none;
                border-radius: {RADIUS_SM}px;
                padding: 4px 12px;
                min-height: 28px;
            }}
            QPushButton:hover {{ background: {BRAND_SUCCESS}; }}
            """
        )

    def show_error(self, message: str, retry_callback=None):
        """Display an error message."""
        self._message_label.setText(message)
        if retry_callback:
            self._retry_btn.clicked.disconnect()
            self._retry_btn.clicked.connect(retry_callback)
            self._retry_btn.show()
        else:
            self._retry_btn.hide()
        self.show()
        self.raise_()

    def hide_error(self):
        """Hide the error banner."""
        self.hide()

    def _on_retry(self):
        """Emit retry signal."""
        pass
