"""
VFX Supervisor Review Tool - Dual Mode Tab

Two toggleable modes:
1. Shot Checker - Review and approve shots
2. Lineup Editor - Build and export timeline
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QLabel
)
from PySide6.QtCore import Qt
import logging

from .shot_review_tab import ShotReviewTab
from .shot_review.lineup_editor_mode import LineupEditorMode
from .shot_review.export_dialog import ExportDialog
from ...core.domain.review_shot import ShotStatus

logger = logging.getLogger(__name__)


class VFXReviewDualModeTab(QWidget):
    """
    VFX Review Tool with two modes:
    - Mode 1: Shot Checker (comparison & review)
    - Mode 2: Lineup Editor (timeline & export)
    """
    
    def __init__(self, config_manager, user_data=None):
        super().__init__()
        
        self.config = config_manager
        self.user_data = user_data or {}
        self._is_closing = False
        self._is_cleaned = False
        
        # Create both modes
        self.shot_checker = ShotReviewTab(config_manager)
        self.lineup_editor = LineupEditorMode()
        
        # Connect signals
        # Connect signals
        # self.lineup_editor.export_requested.connect(self.open_export_dialog) # Signal does not exist in LineupEditorMode
        
        self.setup_ui()
        
        logger.info("VFX Review Dual Mode Tab initialized")
    
    def setup_ui(self):
        """Create dual-mode interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Mode toggle header
        header = self.create_mode_toggle()
        layout.addWidget(header)
        
        # Stacked widget for modes
        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self.shot_checker)   # Index 0
        self.mode_stack.addWidget(self.lineup_editor)  # Index 1
        layout.addWidget(self.mode_stack)
    
    def create_mode_toggle(self):
        """Create mode toggle buttons & Notification Bell"""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1A1A1A;
                border-bottom: 2px solid #2A9D8F;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("VFX SUPERVISOR REVIEW TOOL")
        title.setStyleSheet("QLabel { color: white; font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # --- NOTIFICATION BELL ---
        self.btn_notif = QPushButton("N")
        self.btn_notif.setFixedSize(40, 36)
        self.btn_notif.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 20px; color: #888; }
            QPushButton:hover { color: white; background: #333; border-radius: 4px; }
        """)
        self.btn_notif.clicked.connect(self.show_notifications)
        layout.addWidget(self.btn_notif)
        
        # Badge Label (Hidden by default)
        self.lbl_badge = QLabel("0", self.btn_notif)
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.hide()
        self.lbl_badge.setStyleSheet("""
            background-color: red; color: white; border-radius: 8px; 
            font-size: 10px; font-weight: bold; padding: 2px;
        """)
        self.lbl_badge.resize(16, 16)
        self.lbl_badge.move(22, 2)
        
        # -------------------------
        
        # Mode toggle buttons
        self.btn_shot_checker = QPushButton("Shot Checker")
        self.btn_shot_checker.clicked.connect(lambda: self.switch_mode(0))
        self.btn_shot_checker.setCheckable(True)
        self.btn_shot_checker.setChecked(True)
        self.btn_shot_checker.setStyleSheet("""
            QPushButton {
                background-color: #2A9D8F;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
                border: 2px solid #2A9D8F;
            }
            QPushButton:checked {
                background-color: #21867a;
                border: 2px solid #E9C46A;
            }
            QPushButton:hover {
                background-color: #21867a;
            }
        """)
        layout.addWidget(self.btn_shot_checker)
        
        self.btn_lineup_editor = QPushButton("Lineup Editor")
        self.btn_lineup_editor.clicked.connect(lambda: self.switch_mode(1))
        self.btn_lineup_editor.setCheckable(True)
        self.btn_lineup_editor.setStyleSheet("""
            QPushButton {
                background-color: #264653;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
                border: 2px solid #264653;
            }
            QPushButton:checked {
                background-color: #2A9D8F;
                border: 2px solid #E9C46A;
            }
            QPushButton:hover {
                background-color: #2A9D8F;
            }
        """)
        layout.addWidget(self.btn_lineup_editor)
        
        # Initialize Notification Polling
        try:
            self.init_notifications()
        except Exception as e:
            logger.warning(f"Notification init failed (non-critical): {e}")
        
        return header

    def init_notifications(self):
        self.notifier = None
        self.current_user_ids = self._resolve_notification_user_ids()
        
        try:
            from ...core.domain.notification_manager import NotificationManager
            self.notifier = NotificationManager()
            
            # Start timer only if successful
            from PySide6.QtCore import QTimer
            self.notif_timer = QTimer(self)
            self.notif_timer.timeout.connect(self.check_notifications)
            self.notif_timer.start(10000) # Check every 10s
            self.check_notifications() # Initial check
        except Exception as e:
            logging.exception(f"Notification System Init Failed: {e}")

    def _resolve_notification_user_ids(self):
        ids = []
        for key in ("user_id", "username", "display_name"):
            value = self.user_data.get(key) if isinstance(self.user_data, dict) else None
            if isinstance(value, str) and value.strip():
                ids.append(value.strip())

        # Backward-compatible fallback.
        if not ids:
            ids = ["Artist"]

        deduped = []
        seen = set()
        for item in ids:
            norm = item.lower()
            if norm in seen:
                continue
            seen.add(norm)
            deduped.append(item)
        return deduped

    def _get_unread_notifications(self):
        if not self.notifier:
            return []

        merged = {}
        for user_id in self.current_user_ids:
            for note in self.notifier.get_unread(user_id):
                note_id = note.get("id")
                if note_id:
                    merged[note_id] = note

        return sorted(merged.values(), key=lambda x: x.get("timestamp", 0), reverse=True)

    def check_notifications(self):
        if self._is_closing or not self.notifier:
            return
        try:
            notes = self._get_unread_notifications()
            count = len(notes)
            
            if count > 0:
                self.btn_notif.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 20px; color: #ffcc00; }")
                self.lbl_badge.setText(str(count) if count < 9 else "9+")
                self.lbl_badge.show()
                self.lbl_badge.raise_()
            else:
                self.btn_notif.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 20px; color: #888; }")
                self.lbl_badge.hide()
        except Exception as e:
            logger.warning(f"Failed to update notification badge: {e}")

    def show_notifications(self):
        if self._is_closing or not self.notifier:
            return
        from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout, QPushButton
        
        d = QDialog(self)
        d.setWindowTitle("Notifications")
        d.setMinimumSize(400, 300)
        d.resize(400, 300)
        d.setStyleSheet("background: #222; color: #eee;")
        l = QVBoxLayout(d)
        
        notes = self._get_unread_notifications()
        list_w = QListWidget()
        list_w.setStyleSheet("QListWidget { border: none; background: #2a2a2a; } QListWidget::item { padding: 8px; border-bottom: 1px solid #333; }")
        
        ids_to_clear = []
        for n in notes:
            item = QListWidgetItem(f"[{n['type'].upper()}] {n['message']}")
            list_w.addItem(item)
            ids_to_clear.append(n['id'])
            
        if not notes:
            list_w.addItem("No new notifications.")
            
        l.addWidget(list_w)
        
        btn_clear = QPushButton("Mark All Read")
        btn_clear.setStyleSheet("background: #444; color: white; padding: 6px; border: none;") 
        
        def close_and_clear():
            if self._is_closing or not self.notifier:
                d.accept()
                return
            self.notifier.mark_read(ids_to_clear)
            self.check_notifications() # Refresh UI
            d.accept()
            
        btn_clear.clicked.connect(close_and_clear)
        l.addWidget(btn_clear)
        
        d.exec()
    
    def switch_mode(self, mode_index: int):
        """Switch between modes"""
        self.mode_stack.setCurrentIndex(mode_index)
        
        # Update button states
        self.btn_shot_checker.setChecked(mode_index == 0)
        self.btn_lineup_editor.setChecked(mode_index == 1)
        
        # Sync data when switching to lineup editor
        if mode_index == 1:
            if hasattr(self.shot_checker, 'get_project_context'):
                context = self.shot_checker.get_project_context()
                self.lineup_editor.set_project_context(
                    project_name=context.get("name", ""),
                    project_path=context.get("path")
                )
            self.lineup_editor.set_shots(self.shot_checker.shots)
        
        mode_name = "Shot Checker" if mode_index == 0 else "Lineup Editor"
        logger.info(f"Switched to {mode_name} mode")
    
    def open_export_dialog(self):
        """Open export dialog"""
        # Get approved shots
        approved = [s for s in self.shot_checker.shots if s.status == ShotStatus.APPROVED]
        
        if not approved:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Approved Shots",
                "No approved shots to export.\n\nSwitch to Shot Checker mode and approve shots first."
            )
            return
        
        # Show export dialog with approved shots directly
        dialog = ExportDialog(approved, self)
        dialog.exec()

    def closeEvent(self, event):
        """Propagate close event to child widgets for cleanup."""
        self.cleanup_resources()
        super().closeEvent(event)

    def cleanup_resources(self):
        """Release timers/widgets used by both review modes."""
        if self._is_cleaned:
            return

        self._is_closing = True

        if hasattr(self, "notif_timer") and self.notif_timer.isActive():
            self.notif_timer.stop()

        if hasattr(self, "shot_checker"):
            checker = self.shot_checker
            if hasattr(checker, "cleanup_resources"):
                checker.cleanup_resources()
            checker.close()

        if hasattr(self, "lineup_editor"):
            lineup = self.lineup_editor
            if hasattr(lineup, "cleanup_resources"):
                lineup.cleanup_resources()
            lineup.close()

        self._is_cleaned = True

