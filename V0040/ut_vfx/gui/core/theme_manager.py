import logging
import os
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication

class ThemeManager:
    """
    Centralized Theme Engine for UTCAP.
    Loads global styles, parses tokens, and applies custom typography.
    """
    
    # Global Theme Tokens
    TOKENS = {
        "@BG_MAIN": "#121212",
        "@BG_PANEL": "#1E1E1E",
        "@BG_ELEVATED": "#2A2A2A",
        "@ACCENT": "#00B4D8",
        "@ACCENT_HOVER": "#48CAE4",
        "@TEXT_PRIMARY": "#E0E0E0",
        "@TEXT_MUTED": "#888888",
        "@BORDER": "#333333",
        "@BORDER_FOCUS": "#555555",
        "@RADIUS_SM": "4px",
        "@RADIUS_MD": "8px",
        "@RADIUS_LG": "12px",
        "@DANGER": "#EF476F",
        "@SUCCESS": "#06D6A0",
        "@WARNING": "#FFD166",
        "@FONT_UI": "Inter, Roboto, Segoe UI, sans-serif",
        "@FONT_MONO": "JetBrains Mono, Consolas, monospace"
    }

    @classmethod
    def apply_theme(cls, app: QApplication, ut_vfx_dir: str):
        """
        Applies the global QSS theme to the QApplication.
        Args:
            app: The QApplication instance.
            ut_vfx_dir: The path to the ut_vfx directory.
        """
        # 1. Load Custom Fonts (if available in resources)
        fonts_dir = os.path.join(ut_vfx_dir, "resources", "fonts")
        if os.path.exists(fonts_dir):
            for font_file in os.listdir(fonts_dir):
                if font_file.endswith((".ttf", ".otf")):
                    QFontDatabase.addApplicationFont(os.path.join(fonts_dir, font_file))
        
        # 2. Set Default Font
        default_font = QFont("Inter", 10)
        default_font.setStyleHint(QFont.SansSerif)
        app.setFont(default_font)
        
        # 3. Load QSS File
        qss_path = os.path.join(ut_vfx_dir, "resources", "styles", "main.qss")
        fallback_qss = os.path.join(ut_vfx_dir, "resources", "styles.qss")
        
        stylesheet = ""
        
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                stylesheet = f.read()
        elif os.path.exists(fallback_qss):
             with open(fallback_qss, "r", encoding="utf-8") as f:
                stylesheet = f.read()
                
        if stylesheet:
            # 4. Resolve Tokens
            # Replace longest tokens first to avoid partial collisions:
            # e.g. @BORDER before @BORDER_FOCUS -> "#333333_FOCUS" (invalid color).
            for token, value in sorted(cls.TOKENS.items(), key=lambda kv: len(kv[0]), reverse=True):
                stylesheet = stylesheet.replace(token, value)
                
            # 5. Apply
            app.setStyleSheet(stylesheet)
            logging.info("ThemeManager: Global theme applied successfully.")
        else:
            logging.info(f"ThemeManager: Could not find stylesheet at {qss_path}")
