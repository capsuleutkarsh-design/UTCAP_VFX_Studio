
from PySide6.QtWidgets import QApplication
from .global_config import GlobalConfig
from ..system.adaptation_engine import system_engine

class ThemeManager:
    """
    Manages application standard Dark and Light modes.
    Follows Material Design recommended contrast and color standards.
    """
    
    # Standard Dark Mode (Material Design / VS Code Style)
    DARK_MODE = """
        /* GLOBAL RESET & BASE */
        QMainWindow, QDialog { background-color: #121212; color: #E0E0E0; }
        QWidget { color: #E0E0E0; font-family: 'Segoe UI', Sans-Serif; font-size: 14px; outline: none; }
        
        /* INPUT FIELDS */
        QLineEdit, QTextEdit, QPlainTextEdit { 
            background-color: #1E1E1E; 
            border: 1px solid #3E3E3E; 
            border-radius: 4px; 
            padding: 6px; 
            color: #F0F0F0; 
            selection-background-color: #007ACC;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 1px solid #007ACC;
            background-color: #252526;
        }
        
        /* COMBO BOXES */
        QComboBox { 
            background-color: #1E1E1E; 
            border: 1px solid #3E3E3E; 
            border-radius: 4px; 
            padding: 6px; 
            color: #F0F0F0;
        }
        QComboBox:hover { border: 1px solid #555; }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox QAbstractItemView {
            background-color: #1E1E1E;
            border: 1px solid #3E3E3E;
            selection-background-color: #007ACC;
        }

        /* TABLES */
        QTableWidget { 
            background-color: #121212; 
            border: 1px solid #333; 
            gridline-color: #2D2D2D;
            alternate-background-color: #1E1E1E;
            selection-background-color: #37373D; /* Safety for unstyled cells */
        }
        QHeaderView::section { 
            background-color: #1E1E1E; 
            padding: 6px; 
            border: none; 
            border-bottom: 2px solid #333; 
            font-weight: 600; 
        }
        /* CRITICAL FIX: Prevent 'white lines' gap bleed-through on HighDPI */
        QTableWidget::item {
            border: none;
            padding: 2px;
            outline: none; 
        }
        QTableWidget::item:selected { 
            background-color: #37373D; 
            border: none;
            outline: none;
        }
        QTableWidget::item:focus {
            border: none;
            outline: none;
        }

        /* BUTTONS */
        QPushButton { 
            background-color: #007ACC; 
            color: white; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px; 
            font-weight: 600; 
        }
        QPushButton:hover { background-color: #0098FF; margin-top: -1px; margin-bottom: 1px; }
        QPushButton:pressed { background-color: #005A9E; margin-top: 1px; margin-bottom: -1px; }

        /* SCROLLBARS */
        QScrollBar:vertical { border: none; background: #121212; width: 10px; margin: 0; }
        QScrollBar::handle:vertical { background: #424242; min-height: 30px; border-radius: 5px; }
        QScrollBar::handle:vertical:hover { background: #686868; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }

        /* TABS */
        QTabWidget::pane { border: 1px solid #333; background-color: #121212; }
        QTabBar::tab { 
            background-color: #1E1E1E; 
            color: #AAA; 
            padding: 10px 20px; 
            margin-right: 2px; 
            border-top-left-radius: 4px; 
            border-top-right-radius: 4px; 
            font-weight: 500;
        }
        QTabBar::tab:selected { 
            background-color: #121212; 
            color: white; 
            border-top: 3px solid #007ACC; 
        }

        /* SIDEBAR */
        QListWidget#MainSidebar {
            background-color: #1E1E1E;
            border: none;
            border-right: 1px solid #333;
            outline: none;
            padding-top: 10px;
        }
        QListWidget#MainSidebar::item {
            color: #BBB;
            padding: 12px 20px;
            background: transparent;
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            height: 30px;
        }
        QListWidget#MainSidebar::item:hover { background-color: #2A2D2E; color: white; }
        QListWidget#MainSidebar::item:selected {
            background-color: #37373D;
            color: white;
            border-left: 3px solid #007ACC;
        }
        
        /* TOOLTIPS */
        QToolTip { background-color: #333; color: white; border: 1px solid #555; }
    """
    
    # New Flutter-Inspired Material Theme
    FLUTTER_MODE = """
        /* FLUTTER MATERIAL DARK THEME */
        
        /* 1. Global Reset */
        * {
            font-family: 'Roboto', 'Segoe UI', sans-serif;
            font-size: 11pt;
            color: #E1E1E1;
            outline: none;
        }
        
        /* 2. Surfaces */
        QMainWindow, QDialog { background-color: #121212; }
        QWidget { background-color: transparent; }
        
        /* 3. Cards (Group Boxes, Frames) */
        QGroupBox, QFrame {
            background-color: #1E1E1E;
            border: 1px solid #2C2C2C;
            border-radius: 12px;
            margin-top: 24px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0px 8px;
            color: #BB86FC; /* Material Purple */
            font-weight: bold;
        }
        
        /* 4. Inputs (Filled Style) */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
            background-color: #2D2D2D; /* Surface Overlay */
            border: none;
            border-bottom: 2px solid #444;
            border-radius: 8px 8px 0 0;
            padding: 10px 12px;
            selection-background-color: #BB86FC;
            selection-color: #000;
        }
        QLineEdit:focus, QTextEdit:focus {
            border-bottom: 2px solid #BB86FC;
            background-color: #353535;
        }
        
        /* 5. Buttons (Pill Shape aka 'Staduim Border') */
        QPushButton {
            background-color: #BB86FC;
            color: #000000;
            font-weight: 700;
            border-radius: 18px; /* High radius for pill shape */
            padding: 10px 24px;
            border: none;
        }
        QPushButton:hover {
            background-color: #D0A3FF;
            margin-top: -2px; /* Lift effect */
            margin-bottom: 2px;
        }
        QPushButton:pressed {
            background-color: #9965D6;
            margin-top: 2px;
            margin-bottom: -2px;
        }
        /* Secondary Action Buttons */
        QPushButton#secondary {
            background-color: transparent;
            border: 1px solid #BB86FC;
            color: #BB86FC;
        }
        QPushButton#secondary:hover {
            background-color: rgba(187, 134, 252, 0.1);
        }
        
        /* 6. Tabs (Material Style) */
        QTabWidget::pane { border: none; }
        QTabBar::tab {
            background: transparent;
            color: #888;
            padding: 12px 24px;
            font-weight: bold;
            text-transform: uppercase;
            border-bottom: 3px solid transparent;
        }
        QTabBar::tab:selected {
            color: #BB86FC;
            border-bottom: 3px solid #BB86FC;
        }
        QTabBar::tab:hover {
            background-color: rgba(255, 255, 255, 0.05);
        }
        
        /* 7. Sidebar (Navigation Rail) */
        QListWidget#MainSidebar {
            background-color: #1E1E1E;
            border-right: 1px solid #2C2C2C;
            padding: 10px;
        }
        QListWidget#MainSidebar::item {
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 4px;
            color: #AAA;
        }
        QListWidget#MainSidebar::item:selected {
            background-color: rgba(187, 134, 252, 0.12); /* Purple Tint */
            color: #BB86FC;
        }
        QListWidget#MainSidebar::item:hover {
            background-color: rgba(255, 255, 255, 0.05);
        }
        
        /* 8. Scrollbars (Hidden/Minimal) */
        QScrollBar:vertical {
            background: transparent;
            width: 8px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #444;
            border-radius: 4px;
            min-height: 40px;
        }
        QScrollBar::handle:vertical:hover { background: #666; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """

    # Standard Light Mode (Clean White / Off-White)
    LIGHT_MODE = """
        /* GLOBAL RESET & BASE */
        QMainWindow, QDialog { background-color: #F9F9F9; color: #333333; }
        QWidget { color: #333333; font-family: 'Segoe UI', Sans-Serif; font-size: 14px; outline: none; }
        
        /* INPUT FIELDS */
        QLineEdit, QTextEdit, QPlainTextEdit { 
            background-color: #FFFFFF; 
            border: 1px solid #CCCCCC; 
            border-radius: 4px; 
            padding: 6px; 
            color: #333333; 
            selection-background-color: #B3D7FF;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 1px solid #007ACC;
            background-color: #FFFFFF;
        }
        
        /* COMBO BOXES */
        QComboBox { 
            background-color: #FFFFFF; 
            border: 1px solid #CCCCCC; 
            border-radius: 4px; 
            padding: 6px; 
            color: #333333;
        }
        QComboBox:hover { border: 1px solid #999; }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox QAbstractItemView {
            background-color: #FFFFFF;
            border: 1px solid #CCCCCC;
            selection-background-color: #CCE8FF;
            selection-color: #000;
        }

        /* TABLES */
        QTableWidget { 
            background-color: #FFFFFF; 
            border: 1px solid #DDD; 
            gridline-color: #EEE;
            alternate-background-color: #F5F5F5;
        }
        QHeaderView::section { 
            background-color: #EEEEEE; 
            padding: 6px; 
            border: none; 
            border-bottom: 2px solid #DDD; 
            font-weight: 600; 
            color: #555;
        }
        QTableWidget::item:selected { background-color: #E0F0FF; color: #000; }

        /* BUTTONS */
        QPushButton { 
            background-color: #007ACC; 
            color: white; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px; 
            font-weight: 600; 
        }
        QPushButton:hover { background-color: #0098FF; margin-top: -1px; margin-bottom: 1px; }
        QPushButton:pressed { background-color: #005A9E; margin-top: 1px; margin-bottom: -1px; }

        /* SCROLLBARS */
        QScrollBar:vertical { border: none; background: #F9F9F9; width: 10px; margin: 0; }
        QScrollBar::handle:vertical { background: #C1C1C1; min-height: 30px; border-radius: 5px; }
        QScrollBar::handle:vertical:hover { background: #A8A8A8; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }

        /* TABS */
        QTabWidget::pane { border: 1px solid #DDD; background-color: #F9F9F9; }
        QTabBar::tab { 
            background-color: #E5E5E5; 
            color: #666; 
            padding: 10px 20px; 
            margin-right: 2px; 
            border-top-left-radius: 4px; 
            border-top-right-radius: 4px; 
            font-weight: 500;
        }
        QTabBar::tab:selected { 
            background-color: #F9F9F9; 
            color: #333; 
            border-top: 3px solid #007ACC; 
        }

        /* SIDEBAR */
        QListWidget#MainSidebar {
            background-color: #F0F0F0;
            border: none;
            border-right: 1px solid #DDD;
            outline: none;
            padding-top: 10px;
        }
        QListWidget#MainSidebar::item {
            color: #555;
            padding: 12px 20px;
            background: transparent;
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            height: 30px;
        }
        QListWidget#MainSidebar::item:hover { background-color: #E0E0E0; color: #000; }
        QListWidget#MainSidebar::item:selected {
            background-color: #FFFFFF;
            color: #007ACC;
            border-left: 3px solid #007ACC;
        }
        
        /* TOOLTIPS */
        QToolTip { background-color: #FFF; color: #333; border: 1px solid #CCC; }
    """

    # ── UT_VFX MODE ─────────────────────────────────────────────────────────
    # Design Language: Apple × Teenage Engineering
    # Palette:
    #   Base:     #0A0A0C  (almost-black, warmer than pure black)
    #   Surface:  #101014  (card / panel surface)
    #   Raised:   #17171D  (inputs, elevated elements)
    #   Border:   #1F1F28  (hairline borders)
    #   Text:     #E6E4DC  (warm off-white — Apple-ish)
    #   Dim:      #6B6966  (secondary text, disabled)
    #   Accent:   #FF6B00  (Teenage Engineering signature orange)
    #   Confirm:  #34C759  (success; Apple green)
    #   Danger:   #FF3B30  (Apple red)
    # ─────────────────────────────────────────────────────────────────────────
    UTVFX_MODE = """
        /* ── RESET & BASE ──────────────────────────────────────────────── */
        QMainWindow, QDialog {
            background-color: #0A0A0C;
            color: #E6E4DC;
        }
        QWidget {
            background-color: transparent;
            color: #E6E4DC;
            font-family: 'SF Pro Text', 'Inter', 'Segoe UI', 'Helvetica Neue', sans-serif;
            font-size: 13px;
            outline: none;
        }
        QMainWindow > QWidget,
        QDialog > QWidget {
            background-color: #0A0A0C;
        }

        /* ── SIDEBAR (Navigation Rail) ──────────────────────────────────── */
        QListWidget#MainSidebar {
            background-color: #0D0D10;
            border: none;
            border-right: 1px solid #1A1A22;
            outline: none;
            padding: 8px 0;
        }
        QListWidget#MainSidebar::item {
            color: #6B6B7A;
            padding: 13px 20px;
            background: transparent;
            font-family: 'SF Pro Text', 'Inter', 'Segoe UI', sans-serif;
            font-size: 12px;
            font-weight: 500;
            letter-spacing: 0.2px;
            border-left: 2px solid transparent;
            min-height: 18px;
        }
        QListWidget#MainSidebar::item:hover {
            color: #B8B4AC;
            background-color: rgba(255, 107, 0, 0.06);
            border-left: 2px solid rgba(255, 107, 0, 0.3);
        }
        QListWidget#MainSidebar::item:selected {
            color: #FF6B00;
            background-color: rgba(255, 107, 0, 0.10);
            border-left: 2px solid #FF6B00;
            font-weight: 600;
        }

        /* ── GROUP BOXES (Cards) ────────────────────────────────────────── */
        QGroupBox {
            background-color: #101014;
            border: 1px solid #1A1A22;
            border-radius: 6px;
            margin-top: 20px;
            padding: 10px 12px 12px 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #6B6966;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1.2px;
            text-transform: uppercase;
        }

        /* ── INPUT FIELDS ───────────────────────────────────────────────── */
        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #17171D;
            border: 1px solid #1F1F28;
            border-radius: 4px;
            padding: 7px 10px;
            color: #E6E4DC;
            font-family: 'SF Mono', 'Cascadia Code', 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            selection-background-color: #FF6B00;
            selection-color: #0A0A0C;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border: 1px solid #FF6B00;
            background-color: #1A1A22;
        }
        QLineEdit:disabled {
            color: #3A3A45;
            border-color: #15151A;
        }
        QLineEdit[readOnly="true"] {
            color: #5A5A6A;
            background-color: #0F0F13;
        }

        /* Text Edit (log views, notes) */
        QTextEdit, QPlainTextEdit {
            background-color: #0D0D10;
            border: 1px solid #1A1A22;
            border-radius: 4px;
            padding: 8px;
            color: #B8B4AC;
            font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
            font-size: 11px;
            selection-background-color: rgba(255, 107, 0, 0.35);
            selection-color: #E6E4DC;
        }

        /* ── COMBO BOXES ────────────────────────────────────────────────── */
        QComboBox {
            background-color: #17171D;
            border: 1px solid #1F1F28;
            border-radius: 4px;
            padding: 7px 10px;
            color: #E6E4DC;
            font-size: 12px;
            min-width: 80px;
        }
        QComboBox:hover { border-color: #2E2E3A; }
        QComboBox:focus { border-color: #FF6B00; }
        QComboBox::drop-down {
            border: none;
            width: 20px;
            subcontrol-origin: padding;
            subcontrol-position: right center;
        }
        QComboBox::down-arrow {
            width: 8px;
            height: 8px;
        }
        QComboBox QAbstractItemView {
            background-color: #17171D;
            border: 1px solid #1F1F28;
            border-radius: 4px;
            padding: 4px;
            color: #E6E4DC;
            selection-background-color: rgba(255, 107, 0, 0.15);
            selection-color: #FF6B00;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            padding: 8px 12px;
            min-height: 28px;
            border-radius: 3px;
        }

        /* ── BUTTONS ────────────────────────────────────────────────────── */
        QPushButton {
            background-color: #1A1A22;
            color: #B8B4AC;
            border: 1px solid #252530;
            border-radius: 5px;
            padding: 8px 18px;
            font-size: 12px;
            font-weight: 500;
            letter-spacing: 0.2px;
            min-width: 70px;
        }
        QPushButton:hover {
            background-color: #22222C;
            border-color: #FF6B00;
            color: #E6E4DC;
        }
        QPushButton:pressed {
            background-color: #141418;
            border-color: #CC5500;
        }
        QPushButton:disabled {
            color: #3A3A45;
            background-color: #111116;
            border-color: #18181E;
        }

        /* Primary Action Button */
        QPushButton#primaryButton {
            background-color: #FF6B00;
            color: #0A0A0C;
            border: none;
            border-radius: 5px;
            font-weight: 700;
            font-size: 12px;
            padding: 9px 22px;
            letter-spacing: 0.4px;
        }
        QPushButton#primaryButton:hover {
            background-color: #FF8533;
        }
        QPushButton#primaryButton:pressed {
            background-color: #CC5500;
        }
        QPushButton#primaryButton:disabled {
            background-color: #2A1E10;
            color: #5A4030;
        }

        /* Secondary (ghost) Button */
        QPushButton#secondaryButton {
            background-color: transparent;
            color: #6B6966;
            border: 1px solid #222228;
            border-radius: 5px;
            padding: 8px 18px;
        }
        QPushButton#secondaryButton:hover {
            border-color: #3A3A48;
            color: #B8B4AC;
        }

        /* Danger Button */
        QPushButton#dangerButton {
            background-color: #1C0F0D;
            color: #FF3B30;
            border: 1px solid #2E1510;
            border-radius: 5px;
            padding: 8px 18px;
            font-weight: 600;
        }
        QPushButton#dangerButton:hover {
            background-color: #FF3B30;
            color: #FFFFFF;
            border-color: #FF3B30;
        }

        /* ── CHECKBOXES & RADIO BUTTONS ─────────────────────────────────── */
        QCheckBox, QRadioButton {
            color: #9A978F;
            font-size: 12px;
            spacing: 8px;
        }
        QCheckBox:hover, QRadioButton:hover { color: #E6E4DC; }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #2A2A35;
            border-radius: 3px;
            background-color: #17171D;
        }
        QCheckBox::indicator:checked {
            background-color: #FF6B00;
            border-color: #FF6B00;
        }
        QRadioButton::indicator {
            width: 13px;
            height: 13px;
            border: 1px solid #2A2A35;
            border-radius: 6px;
            background-color: #17171D;
        }
        QRadioButton::indicator:checked {
            background-color: #FF6B00;
            border-color: #FF6B00;
        }

        /* ── SLIDERS ────────────────────────────────────────────────────── */
        QSlider::groove:horizontal {
            height: 3px;
            background: #1F1F28;
            border-radius: 2px;
        }
        QSlider::sub-page:horizontal {
            background: #FF6B00;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #E6E4DC;
            border: none;
            width: 12px;
            height: 12px;
            margin: -5px 0;
            border-radius: 6px;
        }
        QSlider::handle:horizontal:hover {
            background: #FF6B00;
        }

        /* ── TABLES ─────────────────────────────────────────────────────── */
        QTableWidget {
            background-color: #0D0D10;
            border: 1px solid #1A1A22;
            border-radius: 4px;
            gridline-color: #17171D;
            alternate-background-color: #101014;
            color: #B8B4AC;
            font-size: 12px;
            selection-background-color: rgba(255, 107, 0, 0.12);
        }
        QHeaderView::section {
            background-color: #0A0A0C;
            color: #5A5A6A;
            padding: 8px 10px;
            border: none;
            border-right: 1px solid #1A1A22;
            border-bottom: 1px solid #1F1F28;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        QHeaderView::section:hover {
            color: #FF6B00;
        }
        QTableWidget::item {
            border: none;
            padding: 6px 10px;
            outline: none;
        }
        QTableWidget::item:selected {
            background-color: rgba(255, 107, 0, 0.12);
            color: #FF6B00;
            border: none;
            outline: none;
        }
        QTableWidget::item:focus {
            border: none;
            outline: none;
        }

        /* ── TREE WIDGET ────────────────────────────────────────────────── */
        QTreeWidget {
            background-color: #0D0D10;
            border: 1px solid #1A1A22;
            border-radius: 4px;
            color: #B8B4AC;
            alternate-background-color: transparent;
            selection-background-color: rgba(255, 107, 0, 0.10);
        }
        QTreeWidget::item { padding: 5px 6px; border: none; }
        QTreeWidget::item:selected { color: #FF6B00; }
        QTreeWidget::item:hover { background-color: rgba(255, 107, 0, 0.06); }
        QTreeWidget::branch:has-children:closed { color: #5A5A6A; }
        QTreeWidget::branch:has-children:open { color: #FF6B00; }

        /* ── LIST WIDGET (generic, not sidebar) ─────────────────────────── */
        QListWidget:not(#MainSidebar) {
            background-color: #0D0D10;
            border: 1px solid #1A1A22;
            border-radius: 4px;
            color: #B8B4AC;
            outline: none;
        }
        QListWidget:not(#MainSidebar)::item {
            padding: 6px 10px;
        }
        QListWidget:not(#MainSidebar)::item:selected {
            background-color: rgba(255, 107, 0, 0.12);
            color: #FF6B00;
        }
        QListWidget:not(#MainSidebar)::item:hover {
            background-color: rgba(255, 107, 0, 0.06);
        }

        /* ── TABS ───────────────────────────────────────────────────────── */
        QTabWidget::pane {
            border: 1px solid #1A1A22;
            background-color: #0A0A0C;
            border-radius: 0 4px 4px 4px;
        }
        QTabBar::tab {
            background-color: transparent;
            color: #4A4A58;
            padding: 9px 20px;
            margin-right: 1px;
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.3px;
            border-bottom: 2px solid transparent;
        }
        QTabBar::tab:hover {
            color: #9A978F;
        }
        QTabBar::tab:selected {
            color: #E6E4DC;
            border-bottom: 2px solid #FF6B00;
            font-weight: 600;
        }

        /* ── PROGRESS BAR ───────────────────────────────────────────────── */
        QProgressBar {
            background-color: #17171D;
            border: none;
            border-radius: 3px;
            height: 4px;
            color: transparent;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #FF6B00;
            border-radius: 3px;
        }

        /* ── SCROLL BARS ────────────────────────────────────────────────── */
        QScrollBar:vertical {
            border: none;
            background: transparent;
            width: 6px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #252530;
            min-height: 40px;
            border-radius: 3px;
        }
        QScrollBar::handle:vertical:hover { background: #3A3A4A; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            border: none;
            background: transparent;
            height: 6px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background: #252530;
            min-width: 40px;
            border-radius: 3px;
        }
        QScrollBar::handle:horizontal:hover { background: #3A3A4A; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

        /* ── SPLITTER ───────────────────────────────────────────────────── */
        QSplitter::handle {
            background-color: #1A1A22;
        }
        QSplitter::handle:hover {
            background-color: #FF6B00;
        }
        QSplitter::handle:horizontal { width: 1px; }
        QSplitter::handle:vertical { height: 1px; }

        /* ── MENU BAR ───────────────────────────────────────────────────── */
        QMenuBar {
            background-color: #0A0A0C;
            color: #6B6966;
            border-bottom: 1px solid #1A1A22;
            padding: 2px;
            font-size: 12px;
        }
        QMenuBar::item:selected {
            background-color: rgba(255, 107, 0, 0.12);
            color: #E6E4DC;
            border-radius: 3px;
        }
        QMenu {
            background-color: #17171D;
            border: 1px solid #1F1F28;
            border-radius: 6px;
            padding: 4px;
            color: #E6E4DC;
        }
        QMenu::item {
            padding: 8px 20px 8px 12px;
            border-radius: 3px;
            font-size: 12px;
        }
        QMenu::item:selected {
            background-color: rgba(255, 107, 0, 0.14);
            color: #FF6B00;
        }
        QMenu::separator {
            height: 1px;
            background: #1F1F28;
            margin: 4px 8px;
        }

        /* ── STATUS BAR ─────────────────────────────────────────────────── */
        QStatusBar {
            background-color: #0A0A0C;
            border-top: 1px solid #1A1A22;
            color: #4A4A58;
            font-size: 11px;
            font-family: 'SF Mono', 'Consolas', monospace;
        }

        /* ── TOOLBAR ────────────────────────────────────────────────────── */
        QToolBar {
            background-color: #0D0D10;
            border-bottom: 1px solid #1A1A22;
            spacing: 4px;
            padding: 4px 8px;
        }
        QToolButton {
            background: transparent;
            border: none;
            color: #6B6966;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
        }
        QToolButton:hover {
            background-color: rgba(255, 107, 0, 0.08);
            color: #E6E4DC;
        }
        QToolButton:pressed {
            background-color: rgba(255, 107, 0, 0.18);
            color: #FF6B00;
        }

        /* ── LABELS ─────────────────────────────────────────────────────── */
        QLabel {
            color: #9A978F;
            background: transparent;
            font-size: 12px;
        }
        QLabel[heading="true"] {
            color: #E6E4DC;
            font-size: 14px;
            font-weight: 600;
        }

        /* ── TOOLTIPS ───────────────────────────────────────────────────── */
        QToolTip {
            background-color: #1A1A24;
            color: #B8B4AC;
            border: 1px solid #252532;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 11px;
            font-family: 'SF Pro Text', 'Inter', 'Segoe UI', sans-serif;
        }

        /* ── FRAMES ─────────────────────────────────────────────────────── */
        QFrame[frameShape="4"],
        QFrame[frameShape="5"] {
            color: #1A1A22;
        }

        /* ── DIALOG BUTTONS ─────────────────────────────────────────────── */
        QDialogButtonBox QPushButton {
            min-width: 80px;
        }

        /* ── MESSAGE BOX ────────────────────────────────────────────────── */
        QMessageBox {
            background-color: #101014;
            border: 1px solid #1A1A22;
            border-radius: 8px;
        }
        QMessageBox QLabel {
            color: #E6E4DC;
            font-size: 13px;
        }

        /* ── SCROLL AREA ────────────────────────────────────────────────── */
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QScrollArea > QWidget > QWidget {
            background-color: transparent;
        }
    """

    @staticmethod
    def get_available_themes():
        """Compatibility API for modules that cycle themes dynamically."""
        return ["Dark", "UT_VFX", "Light"]

    @staticmethod
    def get_current_theme():
        return GlobalConfig.get("THEME_MODE", "UT_VFX")

    @staticmethod
    def _with_adaptive_scale(base_stylesheet: str) -> str:
        """Append adaptation-engine font sizing when applying theme."""
        try:
            dams = system_engine.generate_stylesheet_dams()
            return f"{base_stylesheet}\n\nQWidget {{ font-size: {dams['font_size_main']}; }}"
        except Exception:
            return base_stylesheet

    @staticmethod
    def apply_theme(mode):
        """
        mode: 'Dark', 'UT_VFX', or 'Light'
        """
        app = QApplication.instance()
        if not app:
            return

        from PySide6.QtGui import QPalette, QColor

        if mode == "Light":
            app.setStyleSheet(ThemeManager._with_adaptive_scale(ThemeManager.LIGHT_MODE))
            GlobalConfig.set("THEME_MODE", "Light")

        elif mode == "Dark":
            app.setStyleSheet(ThemeManager._with_adaptive_scale(ThemeManager.DARK_MODE))
            GlobalConfig.set("THEME_MODE", "Dark")
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(18, 18, 18))
            palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
            palette.setColor(QPalette.Base, QColor(18, 18, 18))
            palette.setColor(QPalette.AlternateBase, QColor(30, 30, 30))
            palette.setColor(QPalette.Text, QColor(224, 224, 224))
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
            palette.setColor(QPalette.Highlight, QColor(0, 122, 204))
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            app.setPalette(palette)

        else:
            # Default: UT_VFX Mode (Apple × Teenage Engineering)
            app.setStyleSheet(ThemeManager._with_adaptive_scale(ThemeManager.UTVFX_MODE))
            GlobalConfig.set("THEME_MODE", "UT_VFX")

            # Force palette to match — prevents white gaps on HiDPI
            bg = QColor(10, 10, 12)       # #0A0A0C
            surface = QColor(16, 16, 20)  # #101014
            text = QColor(230, 228, 220)  # #E6E4DC — warm off-white
            accent = QColor(255, 107, 0)  # #FF6B00 — TE orange

            palette = QPalette()
            palette.setColor(QPalette.Window, bg)
            palette.setColor(QPalette.WindowText, text)
            palette.setColor(QPalette.Base, surface)
            palette.setColor(QPalette.AlternateBase, QColor(22, 22, 28))
            palette.setColor(QPalette.ToolTipBase, QColor(20, 20, 24))
            palette.setColor(QPalette.ToolTipText, text)
            palette.setColor(QPalette.Text, text)
            palette.setColor(QPalette.Button, surface)
            palette.setColor(QPalette.ButtonText, text)
            palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
            palette.setColor(QPalette.Link, accent)
            palette.setColor(QPalette.Highlight, accent)
            palette.setColor(QPalette.HighlightedText, QColor(10, 10, 12))
            app.setPalette(palette)

    @staticmethod
    def toggle_mode():
        order = ["UT_VFX", "Dark", "Light"]
        current = ThemeManager.get_current_theme()
        idx = order.index(current) if current in order else 0
        new_mode = order[(idx + 1) % len(order)]
        ThemeManager.apply_theme(new_mode)

    @staticmethod
    def is_dark_mode():
        return GlobalConfig.get("THEME_MODE", "UT_VFX") in ("Dark", "UT_VFX")

    @staticmethod
    def apply_saved_theme():
        saved = GlobalConfig.get("THEME_MODE", "UT_VFX")
        ThemeManager.apply_theme(saved)
