"""
Design Tokens - Single Source of Truth for UI Values

This module defines all colors, spacing, typography, and other design constants
used throughout the UT_VFX application. By centralizing these values,
we ensure visual consistency and make theme customization trivial.

Usage:
    from ut_vfx.core.infra.design_tokens import ColorTokens as C
    button.setStyleSheet(f"background-color: {C.ACCENT_PRIMARY};")
"""


class ColorTokens:
    """
    Color palette used across the application.
    
    These colors are extracted from the existing inline styles to preserve
    the current visual appearance while enabling centralized management.
    """
    
    # === BACKGROUNDS ===
    BG_PRIMARY = "#121212"      # Main window background
    BG_SURFACE = "#1E1E1E"      # Cards, panels, elevated surfaces
    BG_ELEVATED = "#252525"     # Input fields, elevated elements
    BG_HOVER = "#2A2A2A"        # Hover states for interactive elements
    BG_SIDEBAR = "#111111"      # Sidebar specific (Admin Panel)
    BG_INPUT = "#2D2D2D"        # Input field backgrounds
    
    # Additional background variants from inline styles
    BG_DARK = "#151515"         # Settings card background
    BG_CARD = "#242424"         # Dialog backgrounds
    BG_DARKER = "#0a0a0a"       # Very dark background (thumbnails)
    
    # === ACCENTS ===
    # Primary accent color (cyan) - most commonly used
    ACCENT_PRIMARY = "#00B4D8"   # Primary actions, focus states, links
    ACCENT_HOVER = "#22E0FF"     # Hover state for primary accent
    ACCENT_PRESSED = "#0098B6"   # Pressed/active state
    ACCENT_DARK = "#007B9E"      # Darker accent (primary buttons)
    
    # Alternative accent (used in ThemeManager originally)
    ACCENT_BLUE = "#007ACC"      # ThemeManager's original blue
    
    # Specialty accents (preserve unique colors from specific tabs)
    ACCENT_TEAL = "#2A9D8F"      # Folder Creator success color
    ACCENT_ORANGE = "#e67e22"    # Olive editor button
    ACCENT_WARNING = "#ff9900"   # Timeline warnings, lineup labels
    ACCENT_INFO = "#4a90e2"      # Info text (cache stats in Shot Review)
    ACCENT_CYAN_ALT = "#00d4ff"  # Folder Creator info labels
    
    # === TEXT ===
    TEXT_PRIMARY = "#E0E0E0"     # Main text, high emphasis
    TEXT_SECONDARY = "#AAA"      # Secondary text, medium emphasis
    TEXT_TERTIARY = "#777"       # Tertiary text, low emphasis
    TEXT_DISABLED = "#666"       # Disabled text
    TEXT_INVERSE = "#121212"     # Text on light/accent backgrounds
    TEXT_WHITE = "#FFFFFF"       # Pure white for high contrast
    
    # Additional text variations from inline styles
    TEXT_GRAY_LIGHT = "#888"     # Very common in existing code
    TEXT_GRAY_LIGHTER = "#DCDCDC"  # Folder Creator elements
    TEXT_BEIGE = "#888888"       # Admin Panel sidebar
    TEXT_MUTED = "#6c757d"       # Muted text (commonly used in dashboard)
    
    # === SEMANTIC COLORS ===
    # Success states
    SUCCESS = "#2d5a2d"          # Approve button (Shot Review), dim green
    SUCCESS_DIM = "#1e3a1e"      # Dim success background (Added for Dashboard)
    SUCCESS_BRIGHT = "#4CAF50"   # Bright success (Incoming Delivery)
    SUCCESS_HOVER = "#3d7a3d"    # Hover state for success buttons
    
    # Error/Danger states
    ERROR = "#D32F2F"            # Errors, danger buttons
    ERROR_BRIGHT = "#F44336"     # Hover state for danger
    ERROR_DIM = "#5a2d2d"        # Reject button (Shot Review), dim red
    ERROR_LIGHT = "#ffcdd2"      # Light error text
    
    # Warning states
    WARNING = "#FFAA00"          # Warnings, alerts
    WARNING_ALT = "#ff9900"      # Alternative warning (timeline)
    
    # Info states
    INFO = "#4a90e2"             # Informational text and indicators
    INFO_CYAN = "#00d4ff"        # Cyan info variant
    
    # === BORDERS ===
    BORDER_DEFAULT = "#333"      # Default border color
    BORDER_SUBTLE = "#2C2C2C"    # Subtle borders
    BORDER_FOCUS = "#00B4D8"     # Focus state borders
    BORDER_HOVER = "#38BDF8"     # Hover state borders
    BORDER_LIGHT = "#444"        # Lighter border variant
    
    # === SPECIAL PURPOSE ===
    # Status colors for Live Dashboard PC cards
    STATUS_ONLINE = "#00FF00"    # Online PC status
    STATUS_OFFLINE = "#FF0000"   # Offline PC status
    STATUS_IDLE = "#FFA500"      # Idle PC status
    
    # Progress bar
    PROGRESS_BG = "#111"         # Progress bar background
    PROGRESS_FILL = "#00B4D8"    # Progress bar fill


class SpacingTokens:
    """
    Spacing scale based on 4px increments.
    
    Use these instead of hardcoded pixel values to maintain
    consistent spacing throughout the application.
    """
    XS = 4      # Extra small spacing
    SM = 8      # Small spacing (most common for padding)
    MD = 12     # Medium spacing
    LG = 16     # Large spacing
    XL = 24     # Extra large spacing
    XXL = 32    # 2X large spacing
    
    # Common padding combinations
    PADDING_INPUT = SM          # Standard input padding (8px)
    PADDING_BUTTON = f"{SM}px {LG}px"  # Button padding (8px 16px)
    PADDING_CARD = MD           # Card padding (12px)


class TypographyTokens:
    """
    Typography definitions including fonts and sizes.
    """
    # Font families
    FONT_FAMILY = "'Segoe UI', 'Roboto', sans-serif"
    FONT_UI = "'Segoe UI', 'Roboto', sans-serif"
    FONT_MONO = "'Consolas', 'Courier New', monospace"
    
    # Font sizes (in pixels)
    SIZE_2XS = 8     # Tiny (8px)
    SIZE_XS = 9      # Extra small (9pt in some places)
    SIZE_SM = 10     # Small (10px)
    SIZE_BASE = 12   # Base size for most UI text
    SIZE_MD = 14     # Medium (default for many elements)
    SIZE_LG = 16     # Large
    SIZE_XL = 18     # Extra large
    SIZE_2XL = 24    # Page titles
    SIZE_3XL = 32    # Large headers
    
    # Font weights
    WEIGHT_NORMAL = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700
    
    # Common font-weight values used in code
    WEIGHT_STYLE_NORMAL = "normal"
    WEIGHT_STYLE_BOLD = "bold"


class RadiusTokens:
    """
    Border radius scale for rounded corners.
    """
    NONE = 0     # No rounding
    XS = 2       # Extra small (2px)
    SM = 4       # Small rounding (most common)
    MD = 8       # Medium rounding
    LG = 12      # Large rounding (cards)
    PILL = 18    # Pill-shaped (Flutter theme buttons)
    
    # Common values from existing code
    RADIUS_INPUT = SM      # Input fields
    RADIUS_BUTTON = SM     # Standard buttons
    RADIUS_CARD = LG       # Card containers


class ShadowTokens:
    """
    Box shadow definitions for depth and elevation.
    """
    NONE = "none"
    SM = "0 1px 3px rgba(0, 0, 0, 0.3)"
    MD = "0 4px 6px rgba(0, 0, 0, 0.3)"
    LG = "0 10px 20px rgba(0, 0, 0, 0.4)"
    
    # Elevation levels
    ELEVATION_1 = SM
    ELEVATION_2 = MD
    ELEVATION_3 = LG


class TransitionTokens:
    """
    Animation and transition timing.
    """
    FAST = "100ms"
    NORMAL = "200ms"
    SLOW = "300ms"
    
    # Easing functions
    EASE_IN_OUT = "ease-in-out"
    EASE_OUT = "ease-out"
    EASE_IN = "ease-in"


# Convenience aliases for shorter imports
C = ColorTokens
S = SpacingTokens
T = TypographyTokens
R = RadiusTokens


# Export all token classes
__all__ = [
    'ColorTokens', 'C',
    'SpacingTokens', 'S',
    'TypographyTokens', 'T',
    'RadiusTokens', 'R',
    'ShadowTokens',
    'TransitionTokens',
]
