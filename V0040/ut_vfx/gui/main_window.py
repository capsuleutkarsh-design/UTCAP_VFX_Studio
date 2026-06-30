"""
UT_VFX - MAIN WINDOW
=========================
The primary entry point for the GUI.
Manages tabs, workflow modes, global settings, and styling.

FEATURES:
- Dual Workflow Mode (Standard vs Auto-Scan)
- Professional Dark Theme Loading
- Integrated Reporting and Backup tools
- NEW: Stock Asset Viewer (Proxy Workflow)
- PowerRename Utility
- Offline Update System
"""

import sys
import re
from pathlib import Path
from typing import Optional, Any, Callable, Dict, List, Tuple
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStatusBar, QMessageBox, QStackedWidget,
    QApplication, QDialog, QListWidget, QPushButton
)
from PySide6.QtCore import Qt, QTimer, Signal, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QFileSystemWatcher
from PySide6.QtGui import QAction, QFont, QPalette, QIcon, QKeySequence

# Internal Module Imports
from .. import __version__ as APP_VERSION
from ..core.infra.global_config import GlobalConfig
from ..core.infra.theme_manager import ThemeManager
from ..core.infra.app_context import AppContext
from ..core.infra.database_manager import database_manager
from ..core.domain.workers.db_monitor import DatabaseMonitor
from .components.qt_safety import safe_single_shot

from ..utils.resource_manager import ResourcePathManager
from ..utils.error_handler import error_handler
from ..utils.security import SecurityValidator
from ..utils.reporting import report_generator
from ..utils.backup_recovery import BackupManager, RecoveryManager
from ..core.updater.update_checker import UpdateChecker

from ..core.domain.central_attendance import CentralAttendance
from ..core.infra.network_manager import NetworkManager
from ..gui.notification_overlay import NotificationOverlay
from ..core.infra.telemetry import telemetry
from ..core.system.adaptation_engine import system_engine # [NEW] Adaptation Engine
from ..core.services.sweeper_engine import SweeperEngine
from ..core.services.sweepers.temp_sweeper import TempFileSweeper
from ..gui.help_dialog import show_help  # Re-enabled with JSON-based content

from .tabs.folder_creator_tab import FolderCreatorTab
from .tabs.smart_move_scan_tab import SmartMoveScanTab
from .cap_rename_tab import CapRenameTab 
from .tabs.stock_browser_tab import StockBrowserTab
from .tabs.vfx_review_dual_mode_tab import VFXReviewDualModeTab  # NEW: VFX Supervisor Review Tool (Dual Mode)
from .admin_panel import AdminPanelTab
from .tester_panel import TesterPanel
from .attendance_tab import AttendanceTab
from .login_dialog import LoginDialog
from .tabs.incoming_delivery_tab import IncomingDeliveryTab
from .tabs.settings_tab import SettingsTab
# from ..vfx_dashboard.ui.main_window import MainWindow as DashboardWindow  <-- OLD (UNSAFE)
# from .dashboard_adapter import DashboardAdapter # <-- OLD ADAPTER (REPLACED)

from .tabs.vfx_dashboard_pro.ui.dashboard_widget import DashboardWidget # <-- PRO DASHBOARD
from .tabs.home_tab import HomeTab  # NEW: Cinematic Home Tab



# Component Imports
from .components.workflow_manager import WorkflowManager
from .components.header_builder import HeaderBuilder
from .components.tab_coordinator import TabCoordinator
from .components.session_manager import SessionManagerMixin
from .components.sidebar_controller import SidebarControllerMixin
from .components.quick_search_controller import QuickSearchControllerMixin
from .components.main_window_builder import MainWindowBuilderMixin

class VFXFolderCreatorApp(QMainWindow, SessionManagerMixin, SidebarControllerMixin, QuickSearchControllerMixin, MainWindowBuilderMixin):
    """
    Main application class with responsive UI and enhanced workflow switching.
    """
    attendance_status_signal = Signal(str, str, int)
    
    def __init__(self, user_data=None, app_context=None):
        super().__init__()
        self._is_closing = False
        self._init_complete = False  # Set True at end of init; guards closeEvent
        self._startup_complete = False
        self._logout_requested = False
        self._db_init_worker = None
        self._db_fallback_warned = False
        self._db_runtime_status_cache = {}
        self.attendance_status_signal.connect(self.show_status)
        self.app_context = app_context or AppContext()
        
        # --- SECURITY CONTEXT ---
        self.user_data = user_data
        self.user_role = "Artist"  # Default (kept as string for backward compatibility)
        self.user_display_name = "User"
        
        if self.user_data:
            # Handle both 'roles' array (new) and 'role' string (legacy)
            roles_data = self.user_data.get('roles', self.user_data.get('role', ['Artist']))
            
            # Convert to list if needed
            if isinstance(roles_data, str):
                roles_list = [roles_data]
            elif isinstance(roles_data, list):
                roles_list = roles_data
            else:
                roles_list = ['Artist']
            
            # Keep user_role as STRING (first role for backward compatibility)
            self.user_role = roles_list[0] if roles_list else "Artist"
            
            # Store the full roles list for permission checking
            self.user_roles = roles_list
                
            self.user_display_name = self.user_data.get('display_name', self.user_data.get('user_id', self.user_data.get('username', 'User')))
            self.current_user = self.user_data.get('user_id', self.user_data.get('username', 'debug_user'))
            job_title = self.user_data.get('job_title', self.user_role)
            self.setWindowTitle(f"UT_VFX | {self.user_display_name} ({job_title})")
            
            # --- AUTO ATTENDANCE LOGGING (ASYNC) ---
            safe_single_shot(3000, self, self.perform_async_login)
                
        else:
            self.current_user = "debug_user"
            self.user_roles = ["Artist"]
            self.setWindowTitle(f"UT_VFX Production - {self.user_role} Mode")
        
        # Apply Saved Theme
        ThemeManager.apply_saved_theme()
        # Load Permissions
        self.user_manager = self.app_context.user_manager()
        # Use roles list (not single role string) for permission checking
        self.allowed_tabs = self.user_manager.get_allowed_tabs(self.user_roles)
        
        # DEBUG: Log permissions
        logging.info(f"User: {self.current_user} | Role: {self.user_role}")
        logging.info(f"[ACCESS] Allowed Tabs: {self.allowed_tabs}")
        logging.info(f"[ROLES] All Roles Config: {self.user_manager.roles_config}")
        # ------------------------
        
        self.config_manager = self.app_context.config_manager()
        self.settings = self.config_manager.settings
        self.global_settings = self.settings.get("global_settings", self.config_manager.default_global_settings)
        self.security_validator = SecurityValidator()
        self.report_generator = report_generator
        
        # Initialize Library Manager (DI)
        self.library_manager = self.app_context.library_manager()

        # Initialize Workflow Manager (EXTRACTED COMPONENT)
        self.workflow_manager = WorkflowManager(self)
        self.workflow_manager.mode_changed.connect(self.on_workflow_mode_changed)
        
        # Initialize Header Builder (EXTRACTED COMPONENT)
        self.header_builder = HeaderBuilder(self, self.user_data)

        # Initialize Sweeper Service
        self.sweeper_engine = SweeperEngine(self)
        self.sweeper_engine.register_sweeper(TempFileSweeper(max_age_days=1))  # Daily cleanup of temps > 24h

        # --- NETWORK & NOTIFICATION (SAFE INIT) ---
        if self._is_sqlite_fallback_mode():
            # Fallback mode should avoid central-sync listeners to prevent misleading behavior.
            self.network_manager = None
            self.overlay = None
            logging.warning("Network manager disabled in SQLite fallback mode.")
        else:
            try:
                self.network_manager = NetworkManager(username=self.user_display_name)
                self.network_manager.message_received.connect(self.on_network_message)
                self.network_manager.start()
                self.overlay = NotificationOverlay(self)
                logging.info("Network Manager & Overlay initialized successfully.")
            except Exception as e:
                logging.exception(f"Failed to init Network/Notification systems: {e}", exc_info=True)
                self.network_manager = None
                self.overlay = None

        self.backup_manager = BackupManager()
        self.recovery_manager = RecoveryManager(self.backup_manager)
        
        # 2. Setup Window Properties
        # SMART RESIZE: Responsive to screen resolution
        screen_geo = QApplication.primaryScreen().availableGeometry()
        
        # Use 85% of screen size, but enforce minimums
        target_w = max(1280, int(screen_geo.width() * 0.85))
        target_h = max(800, int(screen_geo.height() * 0.85))
        
        # Ensure we don't exceed screen size
        target_w = min(target_w, screen_geo.width())
        target_h = min(target_h, screen_geo.height())
        
        # [NEW] Apply user scale override, then calculate UI scale based on screen.
        system_engine.set_user_scale_override(self.global_settings.get("ui_scale_override", 0.0))
        system_engine.calculate_ui_scale(screen_geo, self.screen().logicalDotsPerInch())
        
        self.resize(target_w, target_h)
        self.center_window()
        self.setMinimumSize(1024, 768) # Enforce a sensible minimum

        # Set Window Icon
        icon_path = ResourcePathManager.get_icons_dir() / "app_icon_128.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.fix_selection_colors()
        
        # 3. Build UI
        self.init_ui()
        self.init_variables()
        self.apply_stylesheet()
        
        # 4. Restore State
        self.restore_last_paths()
        self.restore_window_geometry()
        
        # 5. Setup Timers & Shortcuts
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.periodic_cleanup)
        self.cleanup_timer.start(300000)  # Run cleanup every 5 minutes
        self.setup_help_shortcuts()
        self.setup_shortcuts()  # NEW: Global keyboard shortcuts (Improvement #9)

        # Update Checker (Auto-Check)
        self.update_checker = UpdateChecker(self)
        # Note: Update callback intentionally disabled - UpdateAvailableDialog handled by UpdateChecker internally
        self.update_checker.start()
        
        # 6. Set Default Workflow Mode
        default_mode_index = 0
        if hasattr(self, 'mode_selector'):
            self.mode_selector.setCurrentIndex(default_mode_index)
            self.workflow_manager.change_workflow_mode(default_mode_index) 

        # Reflect DB runtime mode in UI immediately.
        self._refresh_db_runtime_indicator(show_fallback_warning=True)
        
        logging.info("Application initialized successfully")
        
        # Telemetry: App Start
        telemetry.track_event("app_started", {
            "version": APP_VERSION,
            "role": self.user_role,
            "os": sys.platform
        })
        
        self._init_complete = True
        
        # --- RV Integration Listener ---
        self._setup_rv_listener()

    def _setup_rv_listener(self):
        import os, json
        from pathlib import Path
        
        self.rv_watcher = QFileSystemWatcher(self)
        rv_feedback_dir = Path(os.path.expanduser("~")) / ".utvfx"
        rv_feedback_dir.mkdir(parents=True, exist_ok=True)
        self.rv_feedback_file = str(rv_feedback_dir / "rv_feedback.json")
        
        if not os.path.exists(self.rv_feedback_file):
            with open(self.rv_feedback_file, 'w') as f:
                f.write('{}')
                
        self.rv_watcher.addPath(self.rv_feedback_file)
        self.rv_watcher.fileChanged.connect(self.on_rv_feedback)
        
    def on_rv_feedback(self, path):
        import json, os
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            status = data.get("status")
            media = data.get("media_path")
            if status and media:
                filename = os.path.basename(media)
                level = "success" if status == "approved" else "error"
                
                updated = False
                # Try to find the Dashboard tab and update the shot
                tab = self._get_tab_instance("VFX Dashboard PRO", create=False)
                if tab and hasattr(tab, "all_shots"):
                    media_norm = os.path.normpath(media).lower()
                    for shot in tab.all_shots:
                        render_norm = os.path.normpath(getattr(shot, "render_path", "") or "").lower()
                        scan_norm = os.path.normpath(getattr(shot, "scan_path", "") or "").lower()
                        
                        if media_norm and (media_norm == render_norm or media_norm == scan_norm):
                            # Set status (typically capitalized in DB e.g. "Approved")
                            new_status = status.capitalize()
                            shot.status = new_status
                            if hasattr(shot, "comp_dept") and shot.comp_dept:
                                shot.comp_dept.status = new_status
                                
                            # Bypass the normal save button and call the save handler
                            # Force bypass read-only check just for this if needed, 
                            # but normally Supervisor uses RV.
                            tab.on_shot_save(shot)
                            updated = True
                            break
                            
                if updated:
                    self.show_status(f"RV: {filename} marked as {status.upper()} and saved to DB!", level, 8000)
                else:
                    self.show_status(f"RV: {filename} marked as {status.upper()}", level, 6000)
                    
        except Exception as e:
            import logging
            logging.error(f"Error handling RV feedback: {e}")
        

    
    def fix_selection_colors(self):
        """Fix the blue strips showing white issue across all platforms."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Highlight, Qt.GlobalColor.darkBlue)
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        self.setPalette(palette)
    
    def show_status(self, message: str, level: str = "info", duration: int = 3000):
        """
        Show a color-coded, timed status bar message.

        Args:
            message:  The text to display.
            level:    "info" (white), "success" (green), "warning" (amber), "error" (red)
            duration: Display duration in milliseconds (0 = permanent).
        """
        colors = {
            "info":    "#E2E8F0",   # near-white
            "success": "#4ADE80",   # green
            "warning": "#FCD34D",   # amber
            "error":   "#F87171",   # red
        }
        color = colors.get(level, colors["info"])
        self.status_bar.setStyleSheet(
            f"QStatusBar {{ color: {color}; font-weight: {'bold' if level != 'info' else 'normal'}; }}"
        )
        self.status_bar.showMessage(message, duration)
        if duration > 0:
            # Reset style after message clears
            safe_single_shot(
                duration + 50,
                self,
                lambda: self.status_bar.setStyleSheet(""),
            )

    def show_feedback(self, message: str, level: str = "info", duration: int = 4000, details: str = ""):
        """
        Unified feedback entry point for tabs/widgets.
        - info/success/warning route to status toast
        - error shows toast + optional details dialog
        """
        self.show_status(message, level=level, duration=duration)
        if level == "error" and details:
            QMessageBox.critical(self, "Error Details", details)

    def _on_tab_switched(self, tab_text):
        """Callback when tab is switched (triggered by TabCoordinator)."""
        # Telemetry tracking
        try:
            from ..core.infra.telemetry import telemetry
            telemetry.track_event("tab_switched", {"tab": tab_text})
        except Exception as e:
            logging.debug(f"Telemetry tracking failed: {e}")

    def set_cinematic_mode(self, enabled: bool):
        """
        Disabled: Hiding the sidebar permanently traps the user on the Home tab.
        """
        pass

    def change_workflow_mode(self, index):
        """
        Switch the application layout based on selected workflow.
        
        DELEGATED to WorkflowManager component for better maintainability.
        Kept as wrapper method for backward compatibility.
        """
        # Delegate to workflow manager component
        self.workflow_manager.change_workflow_mode(index)
    
    def on_workflow_mode_changed(self, index, mode_name):
        """Callback when workflow mode changes (triggered by WorkflowManager)."""
        logging.info(f"Workflow changed to: {mode_name}")

    def logout_user(self):
        """Log out current user and return to login dialog."""
        reply = QMessageBox.question(
            self,
            "Log Out",
            "Log out and switch user now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._logout_requested = True
        self.show_status("Logging out...", "info", 1200)
        self.close()

    def _reopen_login_after_logout(self):
        """
        Present login dialog again in the same process and relaunch main window on success.
        """
        app = QApplication.instance()
        if app:
            app.setQuitOnLastWindowClosed(False)

        login = LoginDialog(app_context=self.app_context)
        if login.exec() != QDialog.DialogCode.Accepted or not login.user_data:
            if app:
                app.quit()
            return

        new_window = VFXFolderCreatorApp(login.user_data, app_context=self.app_context)
        if app:
            # Keep strong ref to avoid GC closing the new main window.
            setattr(app, "_ut_active_window", new_window)
            app.setQuitOnLastWindowClosed(True)
        new_window.showMaximized()

    # --- ACTION HANDLERS ---

    def _get_tab_instance(self, label: str, create: bool = False):
        """Resolve a tab instance by label from TabCoordinator (lazy-safe)."""
        tc = getattr(self, "tab_coordinator", None)
        if not tc:
            return None

        if label in tc.tab_instances:
            return tc.tab_instances[label]

        if not create:
            return None

        try:
            idx = tc.tab_labels.index(label)
        except ValueError:
            return None
        return tc.get_or_create_tab(idx)

    def new_project(self):
        reply = QMessageBox.question(
            self, 
            "New Project", 
            "Start a new project?\nThis will clear current input fields.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Yes:
            cleared = 0
            for label in ("Folder Creator", "Scan Manager", "Incoming Delivery"):
                tab = self._get_tab_instance(label, create=False)
                if tab and hasattr(tab, "clear_all"):
                    try:
                        tab.clear_all()
                        cleared += 1
                    except Exception as e:
                        logging.debug(f"New project clear failed for {label}: {e}")

            if cleared:
                self.status_bar.showMessage("New project started", 3000)
            else:
                self.status_bar.showMessage("No loaded workflow tabs to clear", 3000)

    def on_templates_refreshed(self):
        """Called when Settings Tab requests a template refresh."""
        try:
            # Reload merged templates into the shared ConfigManager instance.
            self.config_manager.user_templates = self.config_manager._load_user_templates()
            self.config_manager.templates = self.config_manager._secure_combine_templates()
        except Exception as e:
            logging.warning(f"Template reload failed in ConfigManager: {e}")

        refreshed_labels = []
        refresh_map = (
            ("Folder Creator", "load_templates_to_ui"),
            ("Incoming Delivery", "load_templates"),
            ("Scan Manager", "refresh_templates"),
        )
        for label, method_name in refresh_map:
            tab = self._get_tab_instance(label, create=False)
            if tab and hasattr(tab, method_name):
                try:
                    getattr(tab, method_name)()
                    refreshed_labels.append(label)
                except Exception as e:
                    logging.warning(f"Template refresh failed for {label}: {e}")

        if refreshed_labels:
            joined = ", ".join(refreshed_labels)
            self.status_bar.showMessage(f"Templates refreshed in: {joined}", 3000)
            logging.info(f"Main Window: Refreshed templates in tabs: {joined}")
        else:
            self.status_bar.showMessage("Templates refreshed (new tabs will use latest config)", 3000)

    def on_global_settings_updated(self, updated_settings):
        """Propagate global settings to loaded operation tabs."""
        if not isinstance(updated_settings, dict):
            return

        try:
            self.global_settings = dict(updated_settings)
            self.config_manager.settings["global_settings"] = dict(updated_settings)
            system_engine.set_user_scale_override(updated_settings.get("ui_scale_override", 0.0))
            screen_geo = QApplication.primaryScreen().availableGeometry()
            system_engine.calculate_ui_scale(screen_geo, self.screen().logicalDotsPerInch())
            self.apply_stylesheet()
        except Exception as e:
            logging.debug(f"Failed to cache updated global settings in MainWindow: {e}")

        applied_labels = []
        for label in ("Folder Creator", "Scan Manager", "Incoming Delivery"):
            tab = self._get_tab_instance(label, create=False)
            if tab and hasattr(tab, "apply_global_settings"):
                try:
                    tab.apply_global_settings(updated_settings)
                    applied_labels.append(label)
                except Exception as e:
                    logging.warning(f"Applying global settings failed for {label}: {e}")

        if hasattr(self, "header_builder") and hasattr(self.header_builder, "reload_branding"):
            try:
                self.header_builder.reload_branding()
            except Exception as e:
                logging.warning(f"Header branding refresh failed: {e}")

        if applied_labels:
            self.status_bar.showMessage(
                f"Settings applied to: {', '.join(applied_labels)}",
                3000,
            )
        else:
            self.status_bar.showMessage(
                "Settings saved (will apply when tabs are opened)",
                3000,
            )

    def apply_stylesheet(self):
        try:
            # Use centralized ResourcePathManager to get style
            style_content = ResourcePathManager.get_stylesheet()
            if style_content:
                # [NEW] Inject Dynamic variables
                dams = system_engine.generate_stylesheet_dams()
                
                # Create a "Header" for QSS with variables
                # QSS doesn't support variables natively, so we replace placeholders or append global rules
                # For now, we will perform string replacement if {{var}} exists, 
                # OR we append a * {} block to set global font size (if Qt supported it, but it doesn't really).
                # BETTER APPROACH: We prepend a universal font-size rule for the application.
                
                # 1. Scale Font globally
                font_rule = f"QWidget {{ font-size: {dams['font_size_main']}; }}"
                
                # 2. Append global font rule after base style so wildcard/default sizes
                # in the stylesheet do not override adaptive sizing.
                final_style = f"{style_content}\n\n{font_rule}"
                
                self.setStyleSheet(final_style)
                logging.info(f"Loaded stylesheet with Adaptive Scaling (Base: {dams['font_size_main']})")
            else:
                logging.warning("Stylesheet not found or empty.")
        except Exception as e:
            logging.warning(f"Could not apply stylesheet: {e}")

    def _log_attendance_async(self):
        """Attempts to log attendance in background to avoid freezing UI."""
        if not self.user_data or self._is_closing:
            return
            
        if self._is_sqlite_fallback_mode():
            self.attendance_status_signal.emit(
                "Central attendance auto-log is unavailable in LOCAL MODE.",
                "warning",
                5000,
            )
            return

        username = self.user_data.get('user_id', self.user_data.get('username'))
        if not username:
            self.attendance_status_signal.emit(
                "Attendance skipped: user ID not available.",
                "warning",
                4500,
            )
            return

        from PySide6.QtCore import QRunnable, QThreadPool
        
        class AttendanceWorker(QRunnable):
            def __init__(self, username, is_closing_func, signal):
                super().__init__()
                self.username = username
                self.is_closing = is_closing_func
                self.signal = signal
                
            def run(self):
                import time
                import logging
                from ut_vfx.core.domain.central_attendance import CentralAttendance
                
                last_error = None
                for attempt in range(3):
                    if self.is_closing(): return
                    try:
                        att = CentralAttendance()
                        att.log_action(self.username, 'in')
                        logging.info(f"Attendance Success: {self.username}")
                        if not self.is_closing():
                            self.signal.emit(f"Attendance logged for {self.username}.", "success", 3000)
                        return
                    except Exception as e:
                        last_error = e
                        logging.warning(f"Attendance Attempt {attempt+1} failed: {e}")
                        time.sleep(2)
                        
                if not self.is_closing():
                    self.signal.emit("Attendance auto-log failed. Please use Attendance tab.", "warning", 6000)
                if last_error:
                    logging.error(f"Attendance failed after retries: {last_error}")

        worker = AttendanceWorker(
            username=username,
            is_closing_func=lambda: self._is_closing,
            signal=self.attendance_status_signal
        )
        worker.setAutoDelete(True)
        QThreadPool.globalInstance().start(worker)

    def perform_async_login(self):
        """Log attendance and finish the main window boot sequence."""
        self._log_attendance_async()
        
        # E. Start Background Workers
        if hasattr(self, 'worker_manager'):
            self.worker_manager.start_workers()
        
        # Initiate cinematic mode by default so the home tab is immersive
        self.set_cinematic_mode(True)
        self._switch_to_tab_label("Home")
        
        self._startup_complete = True
        
        # Safety Check: If Home failed to load, the user will be trapped in cinematic mode. Disable it.
        if "Home" not in self.tab_coordinator.tab_instances:
            logging.warning("Home tab failed to load. Disabling cinematic mode fallback to prevent UI trap.")
            self.set_cinematic_mode(False)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.check_system_idle)
        self.idle_timer.start(60000) # Check every minute

        # Start Database Monitor
        self.db_monitor = DatabaseMonitor(interval_sec=5)
        self.db_monitor.connection_status.connect(self.on_db_status_changed)
        self.db_monitor.start()

    def on_db_status_changed(self, is_connected, latency):
        """Update header indicator."""
        if hasattr(self, 'header_builder'):
            self.header_builder.update_db_status(is_connected, latency)
        # Keep runtime mode indicator in sync (handles fallback visibility).
        self._refresh_db_runtime_indicator(show_fallback_warning=False)

    def _refresh_db_runtime_indicator(self, show_fallback_warning: bool = False):
        """Refresh header/status representation of DB runtime mode."""
        try:
            status = database_manager.get_runtime_status()
        except Exception as exc:
            logging.debug("DB runtime status unavailable: %s", exc)
            return
        self._db_runtime_status_cache = status or {}

        active_mode = str(status.get("active_mode", "unknown"))
        fallback_used = bool(status.get("fallback_used", False))

        if hasattr(self, "header_builder") and hasattr(self.header_builder, "set_db_runtime_status"):
            try:
                self.header_builder.set_db_runtime_status(active_mode, fallback_used)
            except Exception as exc:
                logging.debug("DB header mode update skipped: %s", exc)

        self._refresh_system_health_strip(status)

        if show_fallback_warning and fallback_used and not self._db_fallback_warned:
            self._db_fallback_warned = True
            requested_mode = str(status.get("requested_mode", "postgres"))
            msg = (
                f"Database fallback active: requested {requested_mode}, using {active_mode}. "
                "Running in LOCAL MODE (central sync features limited)."
            )
            self.show_status(msg, "warning", 9000)

    def _refresh_system_health_strip(self, status: Optional[dict] = None):
        """Refresh compact runtime health strip in header."""
        if not hasattr(self, "header_builder") or not hasattr(self.header_builder, "set_system_health_status"):
            return
        status = status or self._get_db_runtime_status_cached()

        server_root_value = str(GlobalConfig.get("SERVER_ROOT", "")).strip()
        server_root = Path(server_root_value) if server_root_value else None
        server_root_ok = bool(server_root and server_root.exists() and server_root.is_dir())
        exr_enabled = bool(GlobalConfig.exr_loading_enabled())
        active_mode = str(status.get("active_mode", "")).lower()
        fallback_used = bool(status.get("fallback_used", False))
        sync_enabled = active_mode == "postgres" and not fallback_used

        try:
            self.header_builder.set_system_health_status(
                server_root_ok=server_root_ok,
                exr_enabled=exr_enabled,
                sync_enabled=sync_enabled,
            )
        except Exception as exc:
            logging.debug("Health strip update skipped: %s", exc)

    def _get_db_runtime_status_cached(self) -> dict:
        if self._db_runtime_status_cache:
            return self._db_runtime_status_cache
        try:
            self._db_runtime_status_cache = database_manager.get_runtime_status() or {}
        except Exception as exc:
            logging.debug("DB runtime status cache refresh skipped: %s", exc)
            self._db_runtime_status_cache = {}
        return self._db_runtime_status_cache

    def _is_sqlite_fallback_mode(self) -> bool:
        status = self._get_db_runtime_status_cached()
        active_mode = str(status.get("active_mode", "")).lower()
        fallback_used = bool(status.get("fallback_used", False))
        return active_mode == "sqlite" and fallback_used

    def show_runtime_diagnostics(self):
        status = self._get_db_runtime_status_cached()
        requested_mode = str(status.get("requested_mode", "unknown"))
        active_mode = str(status.get("active_mode", "unknown"))
        fallback_used = bool(status.get("fallback_used", False))
        bootstrap_error = status.get("bootstrap_error")

        server_root_value = str(GlobalConfig.get("SERVER_ROOT", "")).strip()
        server_root = Path(server_root_value) if server_root_value else None
        server_root_ok = bool(server_root and server_root.exists() and server_root.is_dir())
        exr_enabled = bool(GlobalConfig.exr_loading_enabled())

        lines = [
            "Runtime Diagnostics",
            "",
            f"DB requested mode: {requested_mode}",
            f"DB active mode: {active_mode}",
            f"DB fallback used: {fallback_used}",
            f"SERVER_ROOT: {server_root_value or '(not set)'}",
            f"SERVER_ROOT reachable: {server_root_ok}",
            f"EXR loading enabled: {exr_enabled}",
        ]
        if bootstrap_error:
            lines.append(f"DB bootstrap error: {bootstrap_error}")

        QMessageBox.information(self, "Diagnostics", "\n".join(lines))

    def _build_sync_disabled_tab(self, title: str, message: str) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #f8fafc;")
        body_label = QLabel(message)
        body_label.setWordWrap(True)
        body_label.setStyleSheet(
            "font-size: 13px; color: #fbbf24; background: #1f2937; "
            "border: 1px solid #374151; border-radius: 8px; padding: 12px;"
        )
        hint_label = QLabel("Check DB mode in the header or press Ctrl+Shift+D for diagnostics.")
        hint_label.setStyleSheet("font-size: 12px; color: #94a3b8;")

        layout.addWidget(title_label)
        layout.addWidget(body_label)
        layout.addWidget(hint_label)
        layout.addStretch(1)
        return panel

    def check_system_idle(self):
        try:
            from ..core.infra.idle_monitor import IdleMonitor
            monitor = IdleMonitor()
            idle_sec = monitor.get_idle_duration()
            if idle_sec > 600: 
                logging.debug(f"System Idle: {idle_sec:.1f}s")
        except Exception as e:
            logging.debug(f"Idle monitor check failed: {e}")




    # --- NETWORK LISTENERS ---
    def on_network_message(self, msg: dict):
        """Delegated to NetworkHandler."""
        if not hasattr(self, 'network_handler'):
            from .components.network_handler import NetworkHandler
            self.network_handler = NetworkHandler(self)
            
        self.network_handler.on_network_message(msg)

    # perform_remote_wipe moved to NetworkHandler


    def center_window(self):
        """Centers the window on the screen."""
        frame_geo = self.frameGeometry()
        screen = self.screen().availableGeometry().center()
        frame_geo.moveCenter(screen)
        self.move(frame_geo.topLeft())

    def _update_sidebar_responsive_width(self):
        """Reduce sidebar pressure on narrow windows to prevent tab overlap and animate transition smoothly."""
        if not hasattr(self, "sidebar_container") or self.sidebar_container is None:
            return

        if getattr(self, "sidebar_collapsed", False):
            target = 64
        else:
            width = self.width()
            if width < 1280:
                target = 180
            elif width < 1500:
                target = 205
            else:
                target = 240
                
        if self.sidebar_container.width() != target:
            # Stop existing animation if running
            if hasattr(self, "_sidebar_anim") and self._sidebar_anim.state() == QParallelAnimationGroup.Running:
                self._sidebar_anim.stop()
                
            self._sidebar_anim = QParallelAnimationGroup(self)
            
            anim_min = QPropertyAnimation(self.sidebar_container, b"minimumWidth")
            anim_min.setDuration(250)
            anim_min.setEasingCurve(QEasingCurve.InOutQuad)
            anim_min.setStartValue(self.sidebar_container.minimumWidth())
            anim_min.setEndValue(target)
            
            anim_max = QPropertyAnimation(self.sidebar_container, b"maximumWidth")
            anim_max.setDuration(250)
            anim_max.setEasingCurve(QEasingCurve.InOutQuad)
            anim_max.setStartValue(self.sidebar_container.maximumWidth())
            anim_max.setEndValue(target)
            
            self._sidebar_anim.addAnimation(anim_min)
            self._sidebar_anim.addAnimation(anim_max)
            self._sidebar_anim.start()

    def toggle_fullscreen(self):
        """Toggles between Fullscreen and Normal mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def setup_help_shortcuts(self):
        """Setup keyboard shortcuts including help."""
        # Fullscreen Toggle (F11)
        self.fs_shortcut = QAction("Toggle Fullscreen", self)
        self.fs_shortcut.setShortcut(QKeySequence("F11"))
        self.fs_shortcut.triggered.connect(self.toggle_fullscreen)
        self.addAction(self.fs_shortcut)
        
        # Help Dialog (F1) - Re-enabled with JSON content
        self.help_shortcut = QAction("Show Help", self)
        self.help_shortcut.setShortcut(QKeySequence("F1"))
        self.help_shortcut.triggered.connect(self.show_help_dialog)
        self.addAction(self.help_shortcut)
        
        logging.info("Shortcuts registered: F11 (fullscreen), F1 (help)")
    
    def show_help_dialog(self):
        """Show help dialog with documentation."""
        try:
            # Get current tab name from TabCoordinator
            current_tab_name = self.tab_coordinator.get_current_tab_name()
            tab_id = "getting_started"  # Default
            
            # Map current tab name to help tab ID
            tab_mapping = {
                "Tester Panel": "tester",
                "Stock Viewer": "stock_browser",
                "Folder Creator": "folder_creator",
                "Scan Manager": "smart_ingest",
                "CAP Rename": "rename_tool",
                "VFX Dashboard": "dashboard",
                "Attendance": "attendance",
                "Settings": "settings",
                "Admin Panel": "admin_panel",
                "Shot Review": "shot_review"
            }
            
            # Get the help tab ID based on current tab
            tab_id = tab_mapping.get(current_tab_name, "getting_started")
            
            logging.info(f"Opening help for tab: {current_tab_name} (help_id: {tab_id})")
            
            # Show help dialog
            show_help(self, tab_id)
            
        except Exception as e:
            logging.exception(f"Error opening help dialog: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Help Error", 
                f"Could not open help dialog.\n\nError: {str(e)}") 

    def restore_window_geometry(self):
        geo = self.global_settings.get("window_geometry")
        if geo:
            try:
                x, y, w, h = map(int, geo.split(','))
                
                # Validation: Ensure window is visible on current screens
                rect = QRect(x, y, w, h)
                valid = False
                for screen in QApplication.screens():
                    if screen.availableGeometry().intersects(rect):
                        valid = True
                        break
                
                if valid:
                    self.setGeometry(x, y, w, h)
                else:
                    self.center_window()
            except Exception as e:
                logging.exception(f"Error restoring window geometry: {e}")
                self.center_window()
    
    def periodic_cleanup(self):
        """Run background maintenance tasks."""
        if hasattr(self, 'sweeper_engine'):
             self.sweeper_engine.start_sweep()

    # ===== KEYBOARD SHORTCUTS (Improvement #9) =====
    def setup_shortcuts(self):
        """Setup global keyboard shortcuts for power users"""
        from PySide6.QtGui import QShortcut, QKeySequence
        
        # Tab switching: Ctrl+1 through Ctrl+9
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            # Use lambda with default arg to capture current index
            shortcut.activated.connect(lambda idx=i-1: self.switch_to_tab_index(idx))
        
        # Quick search / Command palette (Ctrl+P)
        quick_search = QShortcut(QKeySequence("Ctrl+P"), self)
        quick_search.activated.connect(self.show_quick_search)
        
        # Refresh current tab (F5 or Ctrl+R)
        refresh_f5 = QShortcut(QKeySequence("F5"), self)
        refresh_f5.activated.connect(self.refresh_current_tab)
        
        refresh_ctrl_r = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_ctrl_r.activated.connect(self.refresh_current_tab)
        
        # Settings shortcut (Ctrl+Shift+S)
        settings_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        settings_shortcut.activated.connect(self.show_settings_tab)

        # Diagnostics shortcut (Ctrl+Shift+D)
        diagnostics_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        diagnostics_shortcut.activated.connect(self.show_runtime_diagnostics)

        # Quick actions shortcut (Ctrl+K)
        quick_actions = QShortcut(QKeySequence("Ctrl+K"), self)
        quick_actions.activated.connect(self.show_quick_search)
        
        logging.info("[SHORTCUTS] Registered keyboard shortcuts: Ctrl+1-9, Ctrl+P, Ctrl+K, F5, Ctrl+R, Ctrl+Shift+S, Ctrl+Shift+D")
    
    def switch_to_tab_index(self, index):
        """Switch to tab by numeric index (0-based)"""
        if 0 <= index < self.tab_coordinator.get_tab_count():
            self.sidebar_nav.setCurrentRow(index)
            logging.debug(f"[SHORTCUT] Switched to tab {index+1}")

    def _switch_to_tab_label(self, label: str) -> bool:
        """Switch to tab by exact label."""
        for i, tab_label in enumerate(self.tab_coordinator.tab_labels):
            if tab_label == label:
                self.switch_to_tab_index(i)
                return True
        return False

    def _run_quick_temp_cleanup(self):
        """Run the registered maintenance sweepers immediately."""
        if hasattr(self, "sweeper_engine") and self.sweeper_engine:
            self.sweeper_engine.start_sweep()
            self.show_feedback("Maintenance sweep started.", level="info", duration=2500)
        else:
            self.show_feedback("Sweeper engine is unavailable.", level="warning", duration=3000)

    def _clear_shot_review_cache(self):
        """Clear shot-review cache through the tab contract."""
        review_tab = self._get_tab_instance("Shot Review", create=True)
        if not review_tab:
            self.show_feedback("Shot Review tab is unavailable.", level="warning", duration=3000)
            return
        if hasattr(review_tab, "switch_mode"):
            review_tab.switch_mode(0)
        shot_checker = getattr(review_tab, "shot_checker", None)
        if shot_checker and hasattr(shot_checker, "clear_all_cache"):
            shot_checker.clear_all_cache()
            return
        self.show_feedback("Shot Review cache action is unavailable.", level="warning", duration=3000)

    def _open_named_tab(self, label: str):
        """Open a named tab through coordinator and show status feedback."""
        if not self._switch_to_tab_label(label):
            self.show_feedback(f"Tab '{label}' is not available for this user.", level="warning", duration=3000)
            return
        self.show_feedback(f"Opened {label}.", level="info", duration=1800)

    def _refresh_stock_viewer(self):
        """Refresh the stock browser tab if available."""
        if not self._switch_to_tab_label("Stock Viewer"):
            self.show_feedback("Stock Viewer tab is not available for this user.", level="warning", duration=3000)
            return
        stock_tab = self._get_tab_instance("Stock Viewer", create=True)
        if not stock_tab:
            self.show_feedback("Stock Viewer tab could not be created.", level="error", duration=3000)
            return
        if hasattr(stock_tab, "load_library_from_server"):
            stock_tab.load_library_from_server()
            self.show_feedback("Stock Viewer refresh started.", level="info", duration=2200)
            return
        self.show_feedback("Stock Viewer refresh action is unavailable.", level="warning", duration=3000)

    def _sync_shot_review_to_dashboard(self):
        """Sync shot-review statuses/notes back to dashboard if available."""
        if not self._switch_to_tab_label("Shot Review"):
            self.show_feedback("Shot Review tab is not available for this user.", level="warning", duration=3000)
            return
        review_tab = self._get_tab_instance("Shot Review", create=True)
        if not review_tab:
            self.show_feedback("Shot Review tab could not be created.", level="error", duration=3000)
            return
        if hasattr(review_tab, "switch_mode"):
            review_tab.switch_mode(0)
        shot_checker = getattr(review_tab, "shot_checker", None)
        if shot_checker and hasattr(shot_checker, "sync_to_dashboard"):
            shot_checker.sync_to_dashboard()
            self.show_feedback("Shot Review sync completed.", level="success", duration=2500)
            return
        self.show_feedback("Shot Review sync action is unavailable.", level="warning", duration=3000)

    def trigger_sync_database(self):
        """Trigger the background database sync engine for Local Offline mode."""
        from ..core.domain.sync_worker import SyncWorker
        if hasattr(self, "_sync_worker") and self._sync_worker.sync_manager.is_syncing:
            self.show_feedback("Sync is already in progress.", level="warning", duration=2500)
            return
            
        self._sync_worker = SyncWorker(database_manager)
        self._sync_worker.finished.connect(
            lambda success: self.show_feedback(
                "Database Sync Completed successfully!" if success else "Database Sync Failed. Check logs.",
                level="success" if success else "error",
                duration=3500
            )
        )
        self._sync_worker.start_sync()
        self.show_feedback("Database Sync started in background...", level="info", duration=2500)

    def refresh_current_tab(self):
        """Refresh/reload the current tab if it supports it"""
        current_widget = self.tab_coordinator.get_current_tab()
        if current_widget:
            called_method = None
            for method_name in (
                "refresh",
                "refresh_data",
                "refresh_project",
                "load_library_from_server",
                "reload",
            ):
                if hasattr(current_widget, method_name):
                    getattr(current_widget, method_name)()
                    called_method = method_name
                    break

            if called_method:
                self.status_bar.showMessage("\u2705 Tab refreshed", 2000)
            else:
                self.status_bar.showMessage("\u2139\uFE0F  This tab doesn't support refresh", 2000)
            logging.debug(f"[SHORTCUT] Refresh triggered on {self.tab_coordinator.get_current_tab_name()}")
    
    def show_settings_tab(self):
        """Jump directly to Settings tab"""
        for i, label in enumerate(self.tab_coordinator.tab_labels):
            if label == "Settings":
                self.switch_to_tab_index(i)
                break
    
    def load_plugins(self):
        """Dynamically find and load tabs from 'gui/plugins' directory."""
        try:
            import importlib
            import pkgutil
            import inspect
            from .plugins.plugin_interface import UTVFXPlugin
            
            # Locate the plugins package
            try:
                from . import plugins
                path = plugins.__path__
                prefix = plugins.__name__ + "."
            except ImportError:
                 logging.warning("Plugin package not found.")
                 return

            for _, name, _ in pkgutil.iter_modules(path, prefix):
                try:
                    module = importlib.import_module(name)
                    # Find classes that inherit from UTVFXPlugin
                    for attribute_name in dir(module):
                        attribute = getattr(module, attribute_name)
                        if (inspect.isclass(attribute) and 
                            issubclass(attribute, UTVFXPlugin) and 
                            attribute is not UTVFXPlugin):
                            
                            # Instantiate and Add
                            try:
                                plugin_instance = attribute()
                                
                                # Inject Context
                                context = {
                                    "user_data": self.user_data,
                                    "user_role": self.user_role,
                                    "config_manager": self.config_manager,
                                    "main_window": self
                                }
                                if hasattr(plugin_instance, 'initialize'):
                                    plugin_instance.initialize(context)

                                tab_name = getattr(plugin_instance, 'plugin_name', "Plugin")
                                tab_icon = getattr(plugin_instance, 'plugin_icon', "\U0001F9E9")
                                
                                # Register as eager tab so coordinator handles navigation consistently.
                                self.tab_coordinator.register_tab(
                                    plugin_instance,
                                    tab_name,
                                    icon=tab_icon,
                                )
                                
                                logging.info(f"Loaded Plugin: {name}.{attribute_name}")
                            except Exception as e:
                                logging.exception(f"Failed to instantiate plugin {attribute_name}: {e}")
                                
                except Exception as e:
                    logging.exception(f"Failed to load plugin module {name}: {e}")
                    
        except Exception as e:
            logging.exception(f"Plugin Loader Error: {e}")

