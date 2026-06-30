"""
Header Builder Component.

Creates the application header with:
- Branding (UT_VFX logo)
- Workflow mode selector
- User profile display
- Help button

Extracted from main_window.py for better maintainability.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QRegion
import logging

from ...widgets.db_speed_indicator_compact import DBSpeedIndicatorCompact


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class HeaderBuilder:
    """
    Builds the application header section.
    
    Creates a professional header with branding, controls, and user info.
    """
    
    def __init__(self, parent_window, user_data=None):
        """
        Initialize header builder.
        
        Args:
            parent_window: Reference to main window
            user_data: User information dict with display_name, role, profile_pic_path
        """
        self.parent = parent_window
        self.user_data = user_data or {}
        self.mode_selector = None
        self.logout_button = None
        self.header_widget = None
        self.mark_label = None
        self.vfx_label = None
        self.badge_label = None
        self.profile_text_widget = None
        self.header_layout = None
        self.branding_widget = None
        self.db_mode_label = None
        self.local_mode_label = None
        self.health_label = None
        self.show_runtime_badges = False
    
    def create_header(self):
        """
        Create the complete header widget.
        
        Returns:
            QFrame: The header widget with all components
        """
        logging.info("Building header structure")
        
        # Root Header (Command Center Gradient)
        header_widget = QFrame()
        header_widget.setObjectName("header")
        header_widget.setMinimumHeight(80)
        header_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.header_widget = header_widget
        
        # Gradient styling
        header_widget.setStyleSheet("""
            QFrame#header {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                border-bottom: 1px solid #334155;
            }
            QLabel { background: transparent; border: none; } 
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(32, 10, 32, 10)
        header_layout.setSpacing(20)
        self.header_layout = header_layout
        
        # 1. LEFT: BRANDING
        logo_widget = self._create_branding()
        self.branding_widget = logo_widget
        header_layout.addWidget(logo_widget)
        header_layout.addStretch()
        
        # 2. CENTER: WORKFLOW SELECTOR
        center_widget = self._create_workflow_selector()
        header_layout.addWidget(center_widget)
        header_layout.addStretch()
        
        # 3. RIGHT: HELP BUTTON
        self.help_button = self._create_help_button()  # Store reference
        header_layout.addWidget(self.help_button)

        # 3a. RIGHT: LOGOUT BUTTON
        self.logout_button = self._create_logout_button()
        header_layout.addWidget(self.logout_button)

        # 3a-2. RIGHT: SYNC BUTTON
        self.sync_button = self._create_sync_button()
        header_layout.addWidget(self.sync_button)
        
        # 3b. DB SPEED INDICATOR (Real-time monitoring)
        self.db_speed_indicator = DBSpeedIndicatorCompact()
        header_layout.addWidget(self.db_speed_indicator)
        
        # 3c. DB MODE INDICATOR (sqlite/postgres/fallback)
        self.db_mode_label = QLabel("DB: --")
        self.db_mode_label.setStyleSheet(
            """
            QLabel {
                color: #CBD5E1;
                font-size: 11px;
                font-weight: 600;
                background: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(148, 163, 184, 0.35);
                border-radius: 4px;
                padding: 2px 8px;
            }
            """
        )
        self.db_mode_label.setToolTip("Database runtime mode")
        header_layout.addWidget(self.db_mode_label)

        # 3d. LOCAL MODE BADGE (always visible in fallback mode)
        self.local_mode_label = QLabel("LOCAL MODE")
        self.local_mode_label.setStyleSheet(
            """
            QLabel {
                color: #FDE68A;
                font-size: 10px;
                font-weight: 800;
                background: rgba(120, 53, 15, 0.45);
                border: 1px solid rgba(252, 211, 77, 0.55);
                border-radius: 4px;
                padding: 2px 8px;
                letter-spacing: 0.4px;
            }
            """
        )
        self.local_mode_label.setToolTip("LOCAL MODE: central sync features are limited")
        self.local_mode_label.setVisible(False)
        header_layout.addWidget(self.local_mode_label)

        # 3e. SYSTEM HEALTH STRIP
        self.health_label = ClickableLabel("Health: --")
        self.health_label.setStyleSheet(
            """
            QLabel {
                color: #CBD5E1;
                font-size: 10px;
                font-weight: 600;
                background: rgba(2, 6, 23, 0.75);
                border: 1px solid rgba(100, 116, 139, 0.45);
                border-radius: 4px;
                padding: 2px 8px;
            }
            """
        )
        self.health_label.setToolTip("Runtime health summary")
        self.health_label.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(self.health_label)

        # Runtime badges are intentionally moved to Settings tab.
        self.db_mode_label.setVisible(False)
        self.local_mode_label.setVisible(False)
        self.health_label.setVisible(False)

        # 4. RIGHT: USER PROFILE
        profile_widget = self._create_user_profile()
        header_layout.addWidget(profile_widget)
        
        # Apply initial responsive layout state.
        self.update_responsive_layout(self.parent.width())
        return header_widget

    def _create_db_indicator(self):
        """Create a small led indicator for DB status."""
        lbl = QLabel("●")
        lbl.setStyleSheet("color: #666; font-size: 14px; margin-right: 10px;")
        lbl.setToolTip("Checking connection...")
        return lbl

    def update_db_status(self, is_connected, latency_ms):
        """Update the connection indicator (deprecated - new widget is self-updating)."""
        pass  # DBSpeed IndicatorCompact handles its own updates

    def set_db_runtime_status(self, active_mode: str, fallback_used: bool = False):
        """Update DB mode indicator text and style."""
        if not self.db_mode_label or not self.show_runtime_badges:
            return
        mode = str(active_mode or "unknown").strip().lower()
        label_mode = "Postgres" if mode == "postgres" else "SQLite" if mode == "sqlite" else mode.title()
        suffix = " (Fallback)" if fallback_used else ""
        self.db_mode_label.setText(f"DB: {label_mode}{suffix}")

        if mode == "postgres" and not fallback_used:
            color = "#4ADE80"
            border = "rgba(74, 222, 128, 0.45)"
        elif fallback_used:
            color = "#FCD34D"
            border = "rgba(252, 211, 77, 0.45)"
        else:
            color = "#93C5FD"
            border = "rgba(147, 197, 253, 0.45)"

        self.db_mode_label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                font-size: 11px;
                font-weight: 700;
                background: rgba(15, 23, 42, 0.65);
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 8px;
            }}
            """
        )
        if self.local_mode_label:
            self.local_mode_label.setVisible(bool(fallback_used))

    def set_system_health_status(
        self,
        server_root_ok: bool,
        exr_enabled: bool,
        sync_enabled: bool,
    ):
        """Update compact runtime health strip in header."""
        if not self.health_label or not self.show_runtime_badges:
            return

        server_state = "Server OK" if server_root_ok else "Server Unreachable"
        exr_state = "EXR ON" if exr_enabled else "EXR OFF"
        sync_state = "Sync ON" if sync_enabled else "Sync Limited"
        self.health_label.setText(f"Health: {server_state} | {exr_state} | {sync_state}")

        if server_root_ok and sync_enabled:
            color = "#4ADE80"
            border = "rgba(74, 222, 128, 0.45)"
        elif not server_root_ok:
            color = "#FCA5A5"
            border = "rgba(248, 113, 113, 0.45)"
        else:
            color = "#FCD34D"
            border = "rgba(252, 211, 77, 0.45)"

        self.health_label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                font-size: 10px;
                font-weight: 700;
                background: rgba(2, 6, 23, 0.75);
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 8px;
            }}
            """
        )
    
    def _create_branding(self):
        """Create the UT_VFX branding section."""
        self.mark_label = None
        self.vfx_label = None
        self.badge_label = None

        logo_widget = QWidget()
        logo_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        logo_widget.setStyleSheet("background: transparent; border: none;")
        logo_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(8)

        global_settings = {}
        if hasattr(self.parent, "config_manager"):
            try:
                global_settings = self.parent.config_manager.settings.get("global_settings", {})
            except Exception:
                global_settings = {}
        branding_logo_path = str(global_settings.get("branding_logo_path", "") or "").strip()

        if branding_logo_path and Path(branding_logo_path).exists():
            logo_label = QLabel()
            logo_label.setStyleSheet("background: transparent; border: none;")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            pix = QPixmap(branding_logo_path)
            if not pix.isNull():
                scaled = pix.scaledToHeight(44, Qt.SmoothTransformation)
                logo_label.setPixmap(scaled)
                logo_label.setFixedSize(scaled.size())
                logo_layout.addWidget(logo_label)
                return logo_widget
        
        # "UT"
        mark_label = QLabel("UT")
        mark_label.setObjectName("appLogo")
        mark_label.setStyleSheet("""
            font-family: 'Segoe UI'; 
            font-size: 28px; 
            font-weight: 700; 
            color: #FFFFFF;
            background: transparent;
        """)
        mark_label.setWordWrap(False)
        mark_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        mark_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        mark_label.setMinimumWidth(55)
        self.mark_label = mark_label
        
        # Secondary tag (thin "VFX")
        vfx_label = QLabel("VFX")
        vfx_label.setStyleSheet("""
            font-family: 'Segoe UI'; 
            font-size: 20px; 
            font-weight: 300; 
            color: #E2E8F0;
            background: transparent;
        """)
        vfx_label.setWordWrap(False)
        vfx_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        vfx_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        vfx_label.setMinimumWidth(38)
        self.vfx_label = vfx_label
        vfx_label.setVisible(True)
        
        # "PRO" Badge
        badge_label = QLabel("PRO")
        badge_label.setObjectName("appDescription")
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_label.setStyleSheet("""
            background-color: #3B82F6; 
            color: white; 
            font-family: 'Inter';
            font-size: 9px;
            font-weight: bold;
            padding: 1px 5px; 
            border-radius: 4px;
            margin-top: 10px; 
        """)
        self.badge_label = badge_label
        
        logo_layout.addWidget(mark_label)
        logo_layout.addWidget(vfx_label)
        logo_layout.addWidget(badge_label)
        
        return logo_widget

    def reload_branding(self):
        """Rebuild branding widget (used after settings change)."""
        if not self.header_layout or not self.branding_widget:
            return
        try:
            idx = self.header_layout.indexOf(self.branding_widget)
            if idx < 0:
                return
            old_widget = self.branding_widget
            new_widget = self._create_branding()
            self.header_layout.removeWidget(old_widget)
            old_widget.deleteLater()
            self.header_layout.insertWidget(idx, new_widget)
            self.branding_widget = new_widget
            self.update_responsive_layout(self.parent.width())
        except Exception as exc:
            logging.warning("Header branding reload failed: %s", exc)
    
    def _create_workflow_selector(self):
        """Create the workflow mode selector dropdown."""
        center_container = QWidget()
        center_container.setStyleSheet("background: transparent; border: none;")
        center_layout = QHBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        
        self.mode_selector = QComboBox()
        self.mode_selector.addItems([
            "Standard (Excel Structure)", 
            "Auto-Scan (Auto-Build & Move)", 
            "Incoming Delivery (Smart Ingest)"
        ])
        self.mode_selector.setMinimumWidth(340)
        self.mode_selector.setMinimumHeight(36)
        self.mode_selector.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Styling
        self.mode_selector.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.01);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 4px 16px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: 500;
            }
            QComboBox:hover { 
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.3); 
            }
            QComboBox::drop-down { 
                border: none; 
                background: transparent; 
                width: 20px;
            }
            QComboBox::down-arrow { 
                image: none; 
                border-left: 4px solid transparent; 
                border-right: 4px solid transparent; 
                border-top: 5px solid #CBD5E1; 
                margin-right: 10px; 
            }
            QComboBox QAbstractItemView {
                background-color: #0F172A;
                color: white;
                selection-background-color: #3B82F6;
                selection-color: white;
                border: 1px solid #334155;
                outline: none;
            }
        """)
        
        center_layout.addWidget(self.mode_selector)
        return center_container
    
    def _create_help_button(self):
        """Create the help button."""
        help_btn = QPushButton("Help")
        help_btn.setMinimumHeight(28)
        help_btn.setMinimumWidth(60)
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        help_btn.setToolTip("Open help documentation (F1)")
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(59, 130, 246, 0.15);
                color: #60A5FA;
                border: 1px solid rgba(96, 165, 250, 0.3);
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
                padding: 0px 8px;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.25);
                border: 1px solid rgba(96, 165, 250, 0.5);
                color: #80B5FA;
            }
            QPushButton:pressed {
                background-color: rgba(59, 130, 246, 0.35);
            }
        """)
        return help_btn

    def _create_logout_button(self):
        """Create logout/switch-user button."""
        logout_btn = QPushButton("Log Out")
        logout_btn.setMinimumHeight(28)
        logout_btn.setMinimumWidth(70)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setToolTip("Switch user without restarting manually")
        logout_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(248, 113, 113, 0.12);
                color: #FCA5A5;
                border: 1px solid rgba(252, 165, 165, 0.35);
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
                padding: 0px 8px;
            }
            QPushButton:hover {
                background-color: rgba(248, 113, 113, 0.2);
                border: 1px solid rgba(252, 165, 165, 0.55);
                color: #FECACA;
            }
            QPushButton:pressed {
                background-color: rgba(248, 113, 113, 0.28);
            }
            """
        )
        return logout_btn

    def _create_sync_button(self):
        """Create a sync button for Local Offline Mode."""
        sync_btn = QPushButton("Sync DB")
        sync_btn.setMinimumHeight(28)
        sync_btn.setMinimumWidth(70)
        sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sync_btn.setToolTip("Synchronize local offline changes to the central database")
        sync_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(16, 185, 129, 0.12);
                color: #34D399;
                border: 1px solid rgba(110, 231, 183, 0.35);
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
                padding: 0px 8px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.2);
                border: 1px solid rgba(110, 231, 183, 0.55);
                color: #6EE7B7;
            }
            QPushButton:pressed {
                background-color: rgba(16, 185, 129, 0.28);
            }
            """
        )
        
        # Connect to sync logic via the parent window
        sync_btn.clicked.connect(lambda: self.parent.trigger_sync_database() if hasattr(self.parent, 'trigger_sync_database') else None)
        return sync_btn
    
    def _create_user_profile(self):
        """Create the user profile section with avatar and name."""
        # Get user data
        display_name = self.user_data.get('display_name', 'Guest User')
        # Handle roles array (new format) and role string (legacy)
        roles_data = self.user_data.get('roles', self.user_data.get('role', ['Guest']))
        if isinstance(roles_data, list):
            role = roles_data[0] if roles_data else 'Guest'
        else:
            role = roles_data
        profile_pic = self.user_data.get('profile_pic_path', '')
        
        # Try to get fresh data from user_manager if available
        if hasattr(self.parent, 'user_manager') and hasattr(self.parent, 'current_user'):
            try:
                fresh_data = self.parent.user_manager.users.get(self.parent.current_user)
                if fresh_data:
                    display_name = fresh_data.get('display_name', display_name)
                    # Extract role from roles array
                    fresh_roles = fresh_data.get('roles', fresh_data.get('role', [role]))
                    if isinstance(fresh_roles, list):
                        role = fresh_roles[0] if fresh_roles else role
                    else:
                        role = fresh_roles
                    profile_pic = fresh_data.get('profile_pic_path', profile_pic)
            except Exception as exc:
                logging.debug("User profile refresh failed, using cached data: %s", exc)
        
        # Container
        profile_widget = QWidget()
        profile_widget.setStyleSheet("background: transparent; border: none;")
        profile_layout = QHBoxLayout(profile_widget)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(12)
        
        # Name/Role text
        text_info = QWidget()
        ti_layout = QVBoxLayout(text_info)
        ti_layout.setContentsMargins(0, 0, 0, 0)
        ti_layout.setSpacing(0)
        ti_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        lbl_name = QLabel(display_name)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_name.setStyleSheet(
            "color: #F8FAFC; font-weight: 600; font-size: 13px; " 
            "background: transparent; border: none;"
        )
        
        lbl_role = QLabel(role.upper())
        lbl_role.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_role.setStyleSheet(
            "color: #94A3B8; font-weight: 600; font-size: 11px; " 
            "letter-spacing: 0.5px; background: transparent; border: none;"
        )
        
        ti_layout.addWidget(lbl_name)
        ti_layout.addWidget(lbl_role)
        
        # Avatar
        avatar_label = self._create_avatar(display_name, profile_pic)
        
        profile_layout.addWidget(text_info)
        profile_layout.addWidget(avatar_label)
        self.profile_text_widget = text_info
        
        return profile_widget
    
    def _create_avatar(self, display_name, profile_pic):
        """Create circular avatar with image or initials."""
        avatar_label = QLabel()
        avatar_label.setObjectName("userAvatar")
        avatar_size = 36
        avatar_label.setFixedSize(avatar_size, avatar_size)
        avatar_label.setStyleSheet("background: transparent; border: none;")
        
        pixmap = QPixmap(avatar_size, avatar_size)
        pixmap.fill(Qt.transparent)
        
        source_pix = QPixmap(profile_pic) if profile_pic and Path(profile_pic).exists() else QPixmap()
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QRegion(0, 0, avatar_size, avatar_size, QRegion.Ellipse)
        painter.setClipRegion(path)
        
        if not source_pix.isNull():
            # Use profile picture
            scaled = source_pix.scaled(
                avatar_size, avatar_size, 
                Qt.KeepAspectRatioByExpanding, 
                Qt.SmoothTransformation
            )
            x_off = (scaled.width() - avatar_size) // 2
            y_off = (scaled.height() - avatar_size) // 2
            painter.drawPixmap(-x_off, -y_off, scaled)
        else:
            # Generate initials avatar
            painter.setBrush(QBrush(QColor("#0EA5E9")))  # Sky Blue
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, avatar_size, avatar_size)
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            initials = "".join([n[0] for n in display_name.split()[:2]]).upper() if display_name else "GU"
            painter.drawText(QRect(0, 0, avatar_size, avatar_size), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        avatar_label.setPixmap(pixmap)
        
        return avatar_label
    
    def get_mode_selector(self):
        """Return the workflow mode selector widget."""
        return self.mode_selector

    def update_responsive_layout(self, window_width: int):
        """
        Adjust header density for narrow window widths so branding remains readable.
        """
        if window_width <= 0:
            return

        if self.mode_selector:
            if window_width < 1260:
                self.mode_selector.setMinimumWidth(240)
            elif window_width < 1500:
                self.mode_selector.setMinimumWidth(290)
            else:
                self.mode_selector.setMinimumWidth(340)

        if self.vfx_label:
            # Keep thin "VFX" visible in normal widths, hide only on very tight layouts.
            self.vfx_label.setVisible(window_width >= 980)

        if self.badge_label:
            self.badge_label.setVisible(window_width >= 1180)

        if self.profile_text_widget:
            self.profile_text_widget.setVisible(window_width >= 1120)

        if self.local_mode_label and self.local_mode_label.isVisible():
            self.local_mode_label.setVisible(window_width >= 980)

        if self.health_label and self.show_runtime_badges:
            self.health_label.setVisible(window_width >= 1200)
