"""
Confirmation dialogs and UX utilities for RingForge UI.

Provides styled confirmation dialogs for destructive actions,
keyboard shortcut hints, and reduced-motion support.
"""

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QDialogButtonBox,
)

from core.tokens import (
    BG_PRIMARY, BG_SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY,
    BRAND_PRIMARY, BRAND_DANGER, BRAND_SUCCESS, BRAND_ACCENT,
    FONT_SIZE_BASE, FONT_SIZE_LARGE, FONT_SIZE_XL,
    SPACING_LG, SPACING_MD, SPACING_SM, RADIUS_LG, RADIUS_MD,
    TARGET_MIN_SIZE, ANIM_MODAL,
)

# ─── Confirmation Dialog ───────────────────────────────────────────────


def confirm(
    parent,
    title: str,
    message: str,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
    icon: str = "⚠",
    destructive: bool = False,
    checkbox_text: str = "",
) -> bool:
    """Show a styled confirmation dialog.

    Args:
        parent: Parent widget.
        title: Dialog title.
        message: Main message text.
        confirm_text: Text for the confirm button.
        cancel_text: Text for the cancel button.
        icon: Icon emoji to display.
        destructive: If True, uses danger styling.
        checkbox_text: Optional checkbox label (e.g., "Don't ask again").

    Returns:
        True if confirmed, False if cancelled.
    """
    dialog = QMessageBox(parent)
    dialog.setWindowTitle(title)
    dialog.setStyleSheet(
        f"""
        QMessageBox {{
            background: {BG_PRIMARY};
            color: {TEXT_PRIMARY};
        }}
        QMessageBox QLabel {{
            color: {TEXT_PRIMARY};
            font-size: {FONT_SIZE_BASE}pt;
        }}
        QPushButton {{
            background: {BG_SURFACE};
            color: {TEXT_PRIMARY};
            border: 1px solid {BRAND_PRIMARY};
            border-radius: {RADIUS_MD}px;
            min-height: {TARGET_MIN_SIZE}px;
            padding: {SPACING_SM}px {SPACING_MD}px;
        }}
        QPushButton:hover {{
            background: {BG_SURFACE_HOVER};
        }}
        QPushButton:reject {{
            background: {BG_SURFACE};
            color: {TEXT_SECONDARY};
            border-color: {TEXT_MUTED};
        }}
        """
    )

    dialog.setText(f"{icon} {message}")
    dialog.setInformativeText("")

    confirm_btn = dialog.addButton(confirm_text, QMessageBox.ButtonRole.AcceptRole)
    cancel_btn = dialog.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)

    if destructive:
        confirm_btn.setStyleSheet(
            f"background: {BRAND_DANGER}; color: {BG_PRIMARY};"
        )

    confirm_btn.setMinimumSize(80, 32)
    cancel_btn.setMinimumSize(80, 32)

    if checkbox_text:
        cb = QCheckBox(checkbox_text)
        cb.setStyleSheet(f"color: {TEXT_SECONDARY};")
        dialog.setCheckBox(cb)

    dialog.setDefaultButton(cancel_btn)
    result = dialog.exec()

    checked = False
    if checkbox_text and dialog.checkBox():
        checked = dialog.checkBox().isChecked()

    return result == QMessageBox.DialogCode.Accepted, checked


# ─── Keyboard Shortcut Hints ───────────────────────────────────────────

def create_shortcut_hints() -> str:
    """Return formatted keyboard shortcut help text."""
    from core.tokens import SHORTCUTS
    lines = ["Keyboard Shortcuts", "─" * 30]
    for action, keys in SHORTCUTS.items():
        label = action.replace("_", " ").title()
        lines.append(f"  {keys:20s}  {label}")
    return "\n".join(lines)


# ─── Reduced Motion Support ────────────────────────────────────────────

class ReducedMotionGuard:
    """Context manager that skips animations when reduced motion is enabled.

    Usage:
        with ReducedMotionGuard() as animate:
            if animate:
                create_fade_in(widget)
    """

    def __enter__(self):
        from core.tokens import get_reduced_motion
        self._should_animate = not get_reduced_motion()
        return self._should_animate

    def __exit__(self, *args):
        pass


def animated(func):
    """Decorator that skips animation when reduced motion is enabled.

    Usage:
        @animated
        def show_widget(widget):
            create_fade_in(widget)
    """
    def wrapper(*args, **kwargs):
        from core.tokens import get_reduced_motion
        if get_reduced_motion():
            # Run without animation
            return func(*args, animated=False, **kwargs)
        return func(*args, animated=True, **kwargs)
    return wrapper


# ─── Status Bar Message with Fade ──────────────────────────────────────

def show_status_fade(status_bar, message: str, timeout: int = 4000):
    """Show a status message with fade-out animation.

    Args:
        status_bar: QStatusBar instance.
        message: Message to display.
        timeout: How long to show in ms.
    """
    status_bar.showMessage(message)
    QTimer.singleShot(timeout, lambda: status_bar.showMessage(""))


# ─── Export Confirmation ───────────────────────────────────────────────

def confirm_export(parent, profile_name: str, duration_ms: int) -> bool:
    """Show export confirmation dialog with profile and duration info.

    Returns:
        True if user confirmed export.
    """
    msg = (
        f"Export as {profile_name.upper()} ringtone?\n"
        f"Duration: {duration_ms // 1000:.1f}s"
    )
    result, _ = confirm(
        parent,
        title="Export Ringtone",
        message=msg,
        confirm_text="Export",
        cancel_text="Cancel",
        icon="🎵",
    )
    return result


# ─── Batch Cancel Confirmation ─────────────────────────────────────────

def confirm_batch_cancel(parent, count: int) -> bool:
    """Show confirmation for cancelling batch processing.

    Returns:
        True if user confirmed cancellation.
    """
    msg = f"Cancel processing {count} item(s)? Progress will be lost."
    result, _ = confirm(
        parent,
        title="Cancel Batch",
        message=msg,
        confirm_text="Cancel Batch",
        cancel_text="Keep Processing",
        icon="⏹",
        destructive=True,
    )
    return result


# ─── Overwrite Confirmation ────────────────────────────────────────────

def confirm_overwrite(parent, filename: str) -> bool:
    """Show confirmation for overwriting an existing file.

    Returns:
        True if user confirmed overwrite.
    """
    msg = f"'{filename}' already exists. Overwrite?"
    result, _ = confirm(
        parent,
        title="File Exists",
        message=msg,
        confirm_text="Overwrite",
        cancel_text="Save As",
        icon="📝",
        destructive=False,
    )
    return result
