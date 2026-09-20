"""
RingForge QSS Stylesheets.

Provides pre-built QSS stylesheets organized by component.
All stylesheets are generated from core.tokens.
"""

from core.tokens import token_stylesheet, BRAND_PRIMARY, BG_PRIMARY

# Main application stylesheet
RINGFORGE_STYLESHEET = token_stylesheet()

# Dark theme override for waveforms
WAVEFORM_STYLESHEET = f"""
QWidget {{
    background: {BG_PRIMARY};
}}
"""

# Compact stylesheet for dialogs
COMPACT_STYLESHEET = f"""
QDialog {{
    background: {BG_PRIMARY};
    font-size: 11pt;
}}
QPushButton {{
    min-height: 32px;
}}
"""
