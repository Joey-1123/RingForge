"""
RingForge design tokens for the PySide6 GUI.

Ported from the ringforge-gui-design skill.
All UI colors, spacing, typography, and animation values
trace back to these tokens. No hardcoded values allowed.
"""

import os

# ═══════════════════════════════════════════════════════════════
# COLORS — Catppuccin Mocha palette (WCAG AA compliant)
# ═══════════════════════════════════════════════════════════════

BG_PRIMARY = "#1e1e2e"
BG_SECONDARY = "#181825"
BG_SURFACE = "#313244"
BG_SURFACE_HOVER = "#45475a"
BG_SURFACE_PRESSED = "#585b70"

TEXT_PRIMARY = "#cdd6f4"
TEXT_SECONDARY = "#a6adc8"
TEXT_MUTED = "#6c7086"
TEXT_INVERSE = "#1e1e2e"

BRAND_PRIMARY = "#89b4fa"
BRAND_ACCENT = "#fab387"
BRAND_SUCCESS = "#a6e3a1"
BRAND_DANGER = "#f38ba8"
BRAND_WARNING = "#f9e2af"

WAVEFORM_DEFAULT = "#64748b"
WAVEFORM_SELECTED = "#89b4fa"
CANDIDATE_DEFAULT = "#a6e3a1"
CANDIDATE_TOP = "#fab387"
BEAT_MARKER = "#94a3b8"
PLAYHEAD = "#f38ba8"
HANDLE = "#f9e2af"
HANDLE_FILL = "#f9e2af"

FOCUS_RING = "#89b4fa"
FOCUS_RING_WIDTH = 2
BORDER_DEFAULT = "#45475a"
BORDER_FOCUS = "#89b4fa"

# ═══════════════════════════════════════════════════════════════
# QColor Aliases (for backward compatibility)
# ═══════════════════════════════════════════════════════════════

COLOR_BG = BG_PRIMARY
COLOR_WAVEFORM = WAVEFORM_DEFAULT
COLOR_CANDIDATE = CANDIDATE_DEFAULT
COLOR_SELECTED = WAVEFORM_SELECTED
COLOR_TEXT = TEXT_PRIMARY
COLOR_CURSOR = PLAYHEAD
COLOR_HANDLE = HANDLE

HANDLE_WIDTH = 8
ZOOM_MIN = 1.0
ZOOM_MAX = 50.0
ZOOM_STEP = 1.2

# ═══════════════════════════════════════════════════════════════
# SPACING — 4px grid scale
# ═══════════════════════════════════════════════════════════════

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 20
SPACING_XXL = 24
SPACING_PAGE = 32
SPACING_SECTION = 48

# ═══════════════════════════════════════════════════════════════
# RADIUS
# ═══════════════════════════════════════════════════════════════

RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 16
RADIUS_FULL = 9999

# ═══════════════════════════════════════════════════════════════
# TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════

FONT_FAMILY_SANS = "sans-serif"
FONT_FAMILY_MONO = "monospace"
FONT_SIZE_SMALL = 9
FONT_SIZE_BASE = 11
FONT_SIZE_LARGE = 14
FONT_SIZE_XL = 18
FONT_SIZE_2XL = 24
FONT_WEIGHT_NORMAL = 50
FONT_WEIGHT_BOLD = 80

# ═══════════════════════════════════════════════════════════════
# ANIMATION
# ═══════════════════════════════════════════════════════════════

ANIM_INSTANT = 100
ANIM_FAST = 150
ANIM_NORMAL = 200
ANIM_SLOW = 300
ANIM_MODAL = 250
ANIM_SPRING = 400

# ═══════════════════════════════════════════════════════════════
# FOCUS POLICY
# ═══════════════════════════════════════════════════════════════

FOCUS_POLICY = "StrongFocus"

# ═══════════════════════════════════════════════════════════════
# TARGET SIZES (WCAG 2.5.8)
# ═══════════════════════════════════════════════════════════════

TARGET_MIN_SIZE = 48
BUTTON_MIN_SIZE = (48, 48)

# ═══════════════════════════════════════════════════════════════
# WAVEFORM LAYERS
# ═══════════════════════════════════════════════════════════════

WAVEFORM_LAYERS = {
    "background": BG_PRIMARY,
    "waveform": WAVEFORM_DEFAULT,
    "selected": WAVEFORM_SELECTED,
    "candidate_1": CANDIDATE_TOP,
    "candidate_2": CANDIDATE_DEFAULT,
    "candidate_3": CANDIDATE_DEFAULT,
    "candidate_4": CANDIDATE_DEFAULT,
    "candidate_5": CANDIDATE_DEFAULT,
    "beat_markers": BEAT_MARKER,
    "current_playhead": PLAYHEAD,
    "region_border": BRAND_PRIMARY,
    "handle": HANDLE,
}

# ═══════════════════════════════════════════════════════════════
# SHORTCUTS
# ═══════════════════════════════════════════════════════════════

SHORTCUTS = {
    "play_pause": "Space",
    "stop": "Escape",
    "seek_forward": "Right",
    "seek_backward": "Left",
    "export": "Ctrl+E",
    "export_as": "Ctrl+Shift+S",
    "open_file": "Ctrl+O",
    "quit": "Ctrl+Q",
}

# ═══════════════════════════════════════════════════════════════
# COMPONENT SIZES
# ═══════════════════════════════════════════════════════════════

WAVEFORM_MIN_HEIGHT = 200
MAIN_WINDOW_MIN_WIDTH = 900
MAIN_WINDOW_MIN_HEIGHT = 600
CANDIDATE_LIST_WIDTH = 300

# ═══════════════════════════════════════════════════════════════
# REDUCED MOTION
# ═══════════════════════════════════════════════════════════════

REDUCED_MOTION_SETTING = "ringforge_reduced_motion"


def get_reduced_motion() -> bool:
    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("RingForge", "RingForge")
        return settings.value(REDUCED_MOTION_SETTING, False, type=bool)
    except Exception:
        return False


def token_stylesheet() -> str:
    return f"""
QMainWindow {{ background: {BG_PRIMARY}; }}
QWidget {{ background: {BG_PRIMARY}; }}
QGroupBox {{ background: {BG_SECONDARY}; border: 1px solid {BORDER_DEFAULT}; border-radius: {RADIUS_LG}px; padding: {SPACING_LG}px; }}
QLabel {{ color: {TEXT_PRIMARY}; }}
QPushButton {{ background: {BG_SURFACE}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; border-radius: {RADIUS_MD}px; padding: {SPACING_SM}px {SPACING_MD}px; min-height: {TARGET_MIN_SIZE}px; }}
QPushButton:hover {{ background: {BG_SURFACE_HOVER}; border-color: {BRAND_PRIMARY}; }}
QPushButton:pressed {{ background: {BG_SURFACE_PRESSED}; }}
QPushButton:focus {{ border: {FOCUS_RING_WIDTH}px solid {FOCUS_RING}; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; }}
QLineEdit {{ background: {BG_SURFACE}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; border-radius: {RADIUS_SM}px; }}
QLineEdit:focus {{ border-color: {FOCUS_RING}; }}
QComboBox {{ background: {BG_SURFACE}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; border-radius: {RADIUS_SM}px; }}
QComboBox:focus {{ border-color: {FOCUS_RING}; }}
QProgressBar::chunk {{ background: {BRAND_PRIMARY}; }}
QStatusBar {{ background: {BG_SECONDARY}; color: {TEXT_SECONDARY}; }}
QTabBar::tab:selected {{ border-bottom: 2px solid {BRAND_PRIMARY}; }}
QCheckBox {{ color: {TEXT_PRIMARY}; }}
QFrame {{ border: 1px solid {BORDER_DEFAULT}; }}
"""
