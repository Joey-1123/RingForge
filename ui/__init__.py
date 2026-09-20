"""
RingForge GUI theme and UI module.

Provides design tokens, stylesheets, animations, icons,
empty states, and component factories for the PySide6 desktop application.
"""

from core.tokens import (
    token_stylesheet,
    BRAND_PRIMARY, BRAND_ACCENT, BRAND_SUCCESS, BRAND_DANGER, BRAND_WARNING,
    BG_PRIMARY, BG_SECONDARY, BG_SURFACE, BG_SURFACE_HOVER, BG_SURFACE_PRESSED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_INVERSE,
    WAVEFORM_DEFAULT, WAVEFORM_SELECTED, CANDIDATE_DEFAULT, CANDIDATE_TOP,
    BEAT_MARKER, PLAYHEAD, HANDLE,
    FONT_SIZE_SMALL, FONT_SIZE_BASE, FONT_SIZE_LARGE, FONT_SIZE_XL, FONT_SIZE_2XL,
    ANIM_FAST, ANIM_NORMAL, ANIM_SLOW, ANIM_MODAL,
    TARGET_MIN_SIZE, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, SHORTCUTS,
    WAVEFORM_LAYERS, get_reduced_motion,
)
from ui.theme.animation import PressFeedbackButton, SkeletonWidget, create_fade_in, create_slide_in, create_stagger_animation
from ui.theme.icon_system import Icon, IconButton, ICON_MAP
from ui.empty_state import EmptyState, NoCandidatesEmpty, NoBatchEmpty, ErrorBanner
from ui.dialogs.confirmation import confirm, confirm_export, confirm_batch_cancel, confirm_overwrite, create_shortcut_hints, show_status_fade

__all__ = [
    "token_stylesheet",
    # Tokens
    "BRAND_PRIMARY", "BRAND_ACCENT", "BRAND_SUCCESS", "BRAND_DANGER", "BRAND_WARNING",
    "BG_PRIMARY", "BG_SECONDARY", "BG_SURFACE", "BG_SURFACE_HOVER", "BG_SURFACE_PRESSED",
    "TEXT_PRIMARY", "TEXT_SECONDARY", "TEXT_MUTED", "TEXT_INVERSE",
    "WAVEFORM_DEFAULT", "WAVEFORM_SELECTED", "CANDIDATE_DEFAULT", "CANDIDATE_TOP",
    "BEAT_MARKER", "PLAYHEAD", "HANDLE",
    "FONT_SIZE_SMALL", "FONT_SIZE_BASE", "FONT_SIZE_LARGE", "FONT_SIZE_XL", "FONT_SIZE_2XL",
    "ANIM_FAST", "ANIM_NORMAL", "ANIM_SLOW", "ANIM_MODAL",
    "TARGET_MIN_SIZE", "SPACING_SM", "SPACING_MD", "SPACING_LG", "SPACING_XL",
    "RADIUS_SM", "RADIUS_MD", "RADIUS_LG", "SHORTCUTS",
    "WAVEFORM_LAYERS", "get_reduced_motion",
    # Animation
    "PressFeedbackButton", "SkeletonWidget", "create_fade_in", "create_slide_in", "create_stagger_animation",
    # Icons
    "Icon", "IconButton", "ICON_MAP",
    # Empty states
    "EmptyState", "NoCandidatesEmpty", "NoBatchEmpty", "ErrorBanner",
    # Dialogs
    "confirm", "confirm_export", "confirm_batch_cancel", "confirm_overwrite",
    "create_shortcut_hints", "show_status_fade",
]
