"""
Design System for UT Central Server.
Contains Color Tokens, Typography, and shared styling for the Server Control Panel.
Premium deep dark mode with glassmorphism aesthetics.
"""

class C:
    """Color Tokens"""
    # Backgrounds
    BG_ROOT = "#0B0B0E"          # Deepest background (Root window)
    BG_SURFACE = "#15151A"       # Main surface color (Cards, Panels)
    BG_SURFACE_HOVER = "#1E1E26" # Interactive surface hover
    
    # Borders
    BORDER_DEFAULT = "#262633"   # Subtle borders for cards
    BORDER_FOCUS = "#38384D"     # Active borders
    
    # Text
    TEXT_PRIMARY = "#FFFFFF"     # High contrast headers and values
    TEXT_SECONDARY = "#8B8B9E"   # Subtitles, labels, disabled text
    
    # Accents & States
    ACCENT_PRIMARY = "#007AFF"   # Deep iOS Blue for active generic states
    STATUS_OK = "#10B981"        # Emerald Green (Server Running)
    STATUS_ERROR = "#EF4444"     # Crimson Red (Server Stopped/Error)
    STATUS_WARNING = "#F59E0B"   # Amber (Starting/Stopping)

class T:
    """Typography Tokens"""
    FAMILY = "Segoe UI, -apple-system, sans-serif"
    
    # Weights
    WEIGHT_NORMAL = "400"
    WEIGHT_SEMI = "600"
    WEIGHT_BOLD = "700"

# Global Stylesheet
GLOBAL_STYLESHEET = f"""
    QWidget {{
        font-family: {T.FAMILY};
        color: {C.TEXT_PRIMARY};
    }}
    
    QMainWindow {{
        background-color: {C.BG_ROOT};
    }}
    
    /* Custom Scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {C.BORDER_DEFAULT};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {C.BORDER_FOCUS};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
"""
