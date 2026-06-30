import logging
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QStackedLayout, QGraphicsDropShadowEffect, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QUrl, QTimer, Signal, QThread, QMetaObject, Q_ARG, Slot
from PySide6.QtGui import QColor, QFont

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

from ut_vfx.core.domain.central_attendance import CentralAttendance
from ut_vfx.core.infra.database_manager import database_manager
from ut_vfx.core.system.adaptation_engine import system_engine

class QuickActionBtn(QFrame):
    clicked = Signal()
    def __init__(self, title, subtitle):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(85)
        self.setObjectName("QuickBtn")
        self.setStyleSheet("""
            QFrame#QuickBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.02));
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-top: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
            }
            QFrame#QuickBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.15), stop:1 rgba(255, 255, 255, 0.06));
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-top: 1px solid rgba(255, 255, 255, 0.5);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("background: none; background-color: transparent; border: none; color: white; font-size: 16px; font-weight: 800; letter-spacing: 1px;")
        lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("background: none; background-color: transparent; border: none; color: #a3a3a3; font-size: 12px; font-weight: 500;")
        lbl_sub.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setStyleSheet("""
                QFrame#QuickBtn {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                }
            """)
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setStyleSheet("""
                QFrame#QuickBtn {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.15), stop:1 rgba(255, 255, 255, 0.06));
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-top: 1px solid rgba(255, 255, 255, 0.5);
                    border-radius: 12px;
                }
            """)
            self.clicked.emit()
        super().mouseReleaseEvent(event)

import time

class HomeLoaderWorker(QThread):
    progress = Signal(int, str)
    data_loaded = Signal(list, dict)
    telemetry_loaded = Signal(str, str, str)
    
    def __init__(self, display_name, app_context, parent=None):
        super().__init__(parent)
        self.display_name = display_name
        self.app_context = app_context
        
    def run(self):
        # 1. Warmup
        time.sleep(0.5)
        self.progress.emit(20, "Mounting File Systems...")
        
        # 2. Ping Database
        time.sleep(0.4)
        self.progress.emit(40, "Connecting to PostgreSQL...")
        try:
            database_manager.ping_sync()
        except Exception:
            pass
            
        # 3. Fetch Tasks & Preload Stock Library
        time.sleep(0.4)
        self.progress.emit(60, "Syncing Central Database...")
        
        # Preload the Stock Library into memory so the Stock Browser opens instantly
        try:
            if self.app_context:
                self.app_context.library_manager().load_library()
        except Exception as e:
            logging.exception(f"Error preloading stock library: {e}")
            
        shots = []
        try:
            sql = "SELECT shot_name, status FROM tracking_shots LIMIT 5"
            res = database_manager.execute_query(sql, fetch="all")
            if res:
                for row in res:
                    if isinstance(row, dict):
                        shots.append(row)
                    else:
                        shots.append({"shot_name": row[0], "status": row[1]})
        except Exception as e:
            logging.exception(f"Error async fetching shots: {e}")
            
        # 4. Fetch Attendance
        self.progress.emit(80, "Verifying User Attendance...")
        punch_status = {}
        try:
            uid = self.display_name.lower().strip()
            sql = "SELECT punch_in, punch_out FROM attendance_log WHERE user_id = %s AND day_date = %s"
            from datetime import datetime
            today_str = datetime.now().strftime('%Y-%m-%d')
            res = database_manager.execute_query(sql, (uid, today_str), fetch="all")
            if res:
                row = res[0]
                punch_status['punch_in'] = row['punch_in'] if isinstance(row, dict) else row[0]
                punch_status['punch_out'] = row['punch_out'] if isinstance(row, dict) else row[1]
        except Exception:
            pass

        # 5. Fetch Studio Telemetry
        try:
            from datetime import datetime
            active_projects = database_manager.execute_query("SELECT COUNT(*) AS c FROM tracking_projects WHERE active = 1", fetch="one")
            pending_review = database_manager.execute_query("SELECT COUNT(*) AS c FROM projects", fetch="one")
            
            # Count distinct users who have punched in but not punched out today
            today_str = datetime.now().strftime('%Y-%m-%d')
            artists_online = database_manager.execute_query("SELECT COUNT(DISTINCT user_id) AS c FROM attendance_log WHERE day_date = %s AND punch_out IS NULL", (today_str,), fetch="one")
            
            ap_count = active_projects['c'] if isinstance(active_projects, dict) else (active_projects[0] if active_projects else 0)
            pr_count = pending_review['c'] if isinstance(pending_review, dict) else (pending_review[0] if pending_review else 0)
            ao_count = artists_online['c'] if isinstance(artists_online, dict) else (artists_online[0] if artists_online else 0)
            
            self.telemetry_loaded.emit(str(ap_count), str(pr_count), str(ao_count))
        except Exception as e:
            logging.exception(f"Error async fetching telemetry: {e}")

        # 6. Finalize
        time.sleep(0.3)
        self.progress.emit(100, "Ready!")
        self.data_loaded.emit(shots, punch_status)

class HomeTab(QWidget):
    """
    Cinematic Home Tab combining WebGL background with Glassmorphic PySide6 UI.
    Provides Quick Actions, Attendance, and Light Dashboard Tasks.
    """
    def __init__(self, user_data=None, app_context=None, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.user_data = user_data or {}
        self.app_context = app_context
        self.user_display_name = self.user_data.get('display_name', self.user_data.get('username', 'Artist'))
        self.attendance = CentralAttendance()
        
        self._is_loaded = False
        self._cinematic_ended = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.init_ui()
        
        # Start real background loading sequence
        self.loader_worker = HomeLoaderWorker(self.user_display_name, self.app_context, self)
        self.loader_worker.progress.connect(self._on_load_progress)
        self.loader_worker.data_loaded.connect(self._on_data_loaded)
        self.loader_worker.telemetry_loaded.connect(self._update_telemetry_ui)
        self.loader_worker.start()

    @Slot(str, str, str)
    def _update_telemetry_ui(self, ap_count: str, pr_count: str, ao_count: str):
        if hasattr(self, 'lbl_active_projects'):
            self.lbl_active_projects.setText(ap_count)
        if hasattr(self, 'lbl_pending_review'):
            self.lbl_pending_review.setText(pr_count)
        if hasattr(self, 'lbl_artists_online'):
            self.lbl_artists_online.setText(ao_count)

    def init_ui(self):
        # We use a Stacked Layout to put PySide6 UI ON TOP of QWebEngineView
        self.stack = QStackedLayout(self)
        self.stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # --- LAYER 0: WEBGL BACKGROUND ---
        if HAS_WEBENGINE:
            self.web_view = QWebEngineView()
            
            html_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "assets", "cinematic_bg.html"
            )
            if os.path.exists(html_path):
                self.web_view.setUrl(QUrl.fromLocalFile(html_path))
            else:
                self.web_view.setHtml("<html><body style='background:#000; color:#fff;'>Background missing</body></html>")
                
            self.web_view.titleChanged.connect(self._on_title_changed)
            self.stack.addWidget(self.web_view)
        else:
            # Fallback for systems without QtWebEngineWidgets
            self.web_view = QWidget()
            self.web_view.setStyleSheet("background-color: #0B1220;")
            
            fallback_layout = QVBoxLayout(self.web_view)
            fallback_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel("Background missing (QtWebEngine disabled)")
            lbl.setStyleSheet("color: #444;")
            fallback_layout.addWidget(lbl)
            
            self.stack.addWidget(self.web_view)
        
        # --- LAYER 1: FOREGROUND UI (TRANSPARENT) ---
        self.overlay_widget = QWidget()
        self.overlay_widget.setStyleSheet("background: transparent;")
        self.overlay_widget.hide()
        
        # --- LAYER 1.5: INVISIBLE CLICK CATCHER ---
        self.click_catcher = QPushButton()
        self.click_catcher.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.click_catcher.setStyleSheet("background: rgba(0, 0, 0, 1); border: none;")
        self.click_catcher.setCursor(Qt.CursorShape.PointingHandCursor)
        self.click_catcher.clicked.connect(self._end_cinematic_mode)
        self.stack.addWidget(self.click_catcher)
        
        overlay_layout = QVBoxLayout(self.overlay_widget)
        overlay_layout.setContentsMargins(40, 40, 40, 40)
        overlay_layout.setSpacing(20)
        
        # Top Bar
        top_bar = QHBoxLayout()
        greeting = QLabel(f"Welcome back, {self.user_display_name}")
        greeting.setStyleSheet("""
            color: white; 
            font-size: 28px; 
            font-weight: 300; 
            font-family: 'Inter', sans-serif;
            letter-spacing: 2px;
        """)
        top_bar.addWidget(greeting)
        top_bar.addStretch()
        
        # Punch In / Punch Out Panel
        self.attendance_panel = self._build_glass_panel()
        att_layout = QHBoxLayout(self.attendance_panel)
        att_layout.setContentsMargins(20, 10, 20, 10)
        
        self.lbl_punch_status = QLabel("Status: Unknown")
        self.lbl_punch_status.setStyleSheet("color: #ccc; font-size: 14px;")
        
        self.btn_punch_in = self._build_glass_button("PUNCH IN", "#4ADE80")
        self.btn_punch_out = self._build_glass_button("PUNCH OUT", "#F87171")
        
        self.btn_punch_in.clicked.connect(lambda: self.do_punch("in"))
        self.btn_punch_out.clicked.connect(lambda: self.do_punch("out"))
        
        att_layout.addWidget(self.lbl_punch_status)
        att_layout.addSpacing(20)
        att_layout.addWidget(self.btn_punch_in)
        att_layout.addWidget(self.btn_punch_out)
        
        top_bar.addWidget(self.attendance_panel)
        overlay_layout.addLayout(top_bar)
        
        # Spacer to push content to middle/bottom
        overlay_layout.addStretch()
        
        # --- MIDDLE SECTION: QUICK LAUNCH & RIGHT PANELS ---
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(40)
        
        # 1. Quick Launch Pad (Left side)
        quick_launch_panel = self._build_glass_panel()
        quick_launch_panel.setMinimumWidth(380)
        ql_layout = QVBoxLayout(quick_launch_panel)
        ql_layout.setContentsMargins(20, 20, 20, 20)
        
        ql_title = QLabel("QUICK LAUNCH")
        ql_title.setStyleSheet("color: #38BDF8; font-size: 14px; font-weight: 800; letter-spacing: 3px; background: transparent; border: none;")
        ql_layout.addWidget(ql_title)
        
        grid_layout = QVBoxLayout()
        grid_layout.setSpacing(15)
        
        row1 = QHBoxLayout()
        btn_rename = self._build_quick_action_btn("📝 File Renamer", "CAP Rename Utility")
        btn_rename.clicked.connect(lambda: self._trigger_tab("CAP Rename"))
        btn_attendance = self._build_quick_action_btn("🕒 Attendance", "Login / Logout & Timesheets")
        btn_attendance.clicked.connect(lambda: self._trigger_tab("Attendance"))
        row1.addWidget(btn_rename)
        row1.addWidget(btn_attendance)
        
        grid_layout.addLayout(row1)
        ql_layout.addLayout(grid_layout)
        
        middle_layout.addWidget(quick_launch_panel, 0, Qt.AlignmentFlag.AlignLeft)
        
        middle_layout.addStretch() # Push right panels to the right
        
        # 2. Right Side Panels (Tasks & Stats)
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setSpacing(20)
        
        # A. Light Tasks Panel
        tasks_panel = self._build_glass_panel()
        tasks_panel.setMinimumWidth(320)
        tasks_layout = QVBoxLayout(tasks_panel)
        tasks_layout.setContentsMargins(20, 20, 20, 20)
        
        tasks_title = QLabel("MY RECENT TASKS")
        tasks_title.setStyleSheet("color: #38BDF8; font-size: 14px; font-weight: 800; letter-spacing: 3px; background: transparent; border: none;")
        tasks_layout.addWidget(tasks_title)
        
        # We will populate actual shots later from worker
        self.tasks_container_layout = QVBoxLayout()
        
        empty_lbl = QLabel("Loading assigned shots...")
        empty_lbl.setStyleSheet("background: none; background-color: transparent; border: none; color: #888; font-style: italic;")
        self.tasks_container_layout.addWidget(empty_lbl)
        
        tasks_layout.addLayout(self.tasks_container_layout)
                
        right_panel_layout.addWidget(tasks_panel)
        
        # B. Studio Stats Panel
        stats_panel = self._build_glass_panel()
        stats_panel.setMinimumWidth(320)
        stats_layout = QVBoxLayout(stats_panel)
        stats_layout.setContentsMargins(20, 20, 20, 20)
        
        stats_title = QLabel("LIVE STUDIO TELEMETRY")
        stats_title.setStyleSheet("color: #38BDF8; font-size: 14px; font-weight: 800; letter-spacing: 3px; background: transparent; border: none;")
        stats_layout.addWidget(stats_title)
        
        stat_row = QHBoxLayout()
        w1, self.lbl_active_projects = self._build_stat_item("Active Projects", "-")
        w2, self.lbl_pending_review = self._build_stat_item("Pending Review", "-")
        w3, self.lbl_artists_online = self._build_stat_item("Artists Online", "-")
        stat_row.addWidget(w1)
        stat_row.addWidget(w2)
        stat_row.addWidget(w3)
        stats_layout.addLayout(stat_row)
        
        right_panel_layout.addWidget(stats_panel)
        
        middle_layout.addLayout(right_panel_layout)
        
        overlay_layout.addLayout(middle_layout)
        
        # Extra spacer at bottom so it clears the cinematic status text
        overlay_layout.addSpacing(100)
        
        self.stack.addWidget(self.overlay_widget)
        
        # Punch UI is updated when data loads

    def showEvent(self, event):
        super().showEvent(event)
        # Force cinematic mode on the main window just in case it didn't stick
        if not getattr(self, '_cinematic_ended', False):
            host = self.window()
            if hasattr(host, 'set_cinematic_mode'):
                host.set_cinematic_mode(True)

    def _build_glass_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("GlassPanel")
        frame.setStyleSheet("""
            QFrame#GlassPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.02));
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-top: 1px solid rgba(255, 255, 255, 0.3);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        frame.setGraphicsEffect(shadow)
        return frame

    def _build_glass_button(self, text: str, color_hex: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {color_hex};
                color: {color_hex};
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {color_hex};
                color: black;
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
        """)
        return btn

    def _build_quick_action_btn(self, title: str, subtitle: str) -> QFrame:
        btn = QuickActionBtn(title, subtitle)
        return btn

    def _build_stat_item(self, label: str, value: str):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        v = QLabel(value)
        v.setStyleSheet("background: none; background-color: transparent; border: none; color: #4ADE80; font-size: 28px; font-weight: 900; font-family: monospace;")
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        l = QLabel(label)
        l.setStyleSheet("background: none; background-color: transparent; border: none; color: #94A3B8; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lay.addWidget(v)
        lay.addWidget(l)
        
        return w, v

    def _trigger_tab(self, tab_label: str):
        host = self.window()
        if hasattr(host, "_switch_to_tab_label"):
            host._switch_to_tab_label(tab_label)

    def _on_load_progress(self, pct, msg):
        if HAS_WEBENGINE:
            safe_msg = msg.replace("'", "\\'")
            self.web_view.page().runJavaScript(
                f"if (typeof window.setLoadingProgress === 'function') {{ window.setLoadingProgress({pct}, '{safe_msg}'); }}"
            )
        
    def _on_data_loaded(self, shots, punch_status):
        self._is_loaded = True
        self.setFocus() # Grab focus so Enter key works
        
        # Clear loading label
        while self.tasks_container_layout.count():
            item = self.tasks_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Populate real tasks
        if not shots:
            empty_lbl = QLabel("No shots assigned to you currently.")
            empty_lbl.setStyleSheet("background: none; background-color: transparent; border: none; color: #888; font-style: italic;")
            self.tasks_container_layout.addWidget(empty_lbl)
        else:
            for s in shots[:5]:
                row = QHBoxLayout()
                lbl_name = QLabel(s.get('shot_name', 'Unknown Shot'))
                lbl_name.setStyleSheet("background: none; background-color: transparent; border: none; color: white; font-weight: bold;")
                
                lbl_status = QLabel(s.get('status', 'WIP'))
                lbl_status.setStyleSheet("color: #1976d2; font-weight: bold; padding: 2px 8px; border-radius: 4px; background-color: rgba(25, 118, 210, 0.2);")
                
                row.addWidget(lbl_name)
                row.addStretch()
                row.addWidget(lbl_status)
                self.tasks_container_layout.addLayout(row)
                
        # Update punch status
        self._cached_punch = punch_status
        self._refresh_punch_buttons(punch_status)

    def _on_title_changed(self, title):
        if title == "CINEMATIC_ENDED" and not self._cinematic_ended:
            self._end_cinematic_mode()

    def keyPressEvent(self, event):
        if self._is_loaded and not self._cinematic_ended:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._end_cinematic_mode()
        super().keyPressEvent(event)

    def _end_cinematic_mode(self):
        self._cinematic_ended = True
        if HAS_WEBENGINE:
            self.web_view.page().runJavaScript("window.triggerEnter()")
        
        # Restore Main Window UI
        host = getattr(self, "main_window", None) or self.window()
        if hasattr(host, 'set_cinematic_mode'):
            try:
                host.set_cinematic_mode(False)
            except Exception as e:
                logging.exception(f"Error ending cinematic mode: {e}")
            
        if hasattr(self, 'click_catcher'):
            self.click_catcher.hide()
            
        self._show_overlay()

    def _show_overlay(self):
        # Fake a fade-in (QWebEngine doesn't play perfectly with PySide opacity animation sometimes, 
        # but we can just show it directly since the WebGL background shifts).
        self.overlay_widget.show()
        # Bring it to front just in case
        self.overlay_widget.raise_()

    # (Legacy _fetch_my_shots removed)

    def _refresh_punch_buttons(self, punch_status):
        pi = punch_status.get('punch_in')
        po = punch_status.get('punch_out')
        
        if not pi and not po:
            self.lbl_punch_status.setText("Status: Not Punched In")
            self.btn_punch_in.setEnabled(True)
            self.btn_punch_out.setEnabled(False)
        elif pi and not po:
            self.lbl_punch_status.setText(f"Status: Punched In ({pi})")
            self.btn_punch_in.setEnabled(False)
            self.btn_punch_out.setEnabled(True)
        elif pi and po:
            self.lbl_punch_status.setText(f"Status: Punched Out ({po})")
            self.btn_punch_in.setEnabled(False)
            self.btn_punch_out.setEnabled(False)
            
    def _update_punch_ui(self):
        """Update punch UI from cached DB fetch, or do a live fallback fetch"""
        if hasattr(self, '_cached_punch'):
            self._refresh_punch_buttons(self._cached_punch)
        else:
            # Fallback if accessed before load finishes
            pass

    def do_punch(self, action: str):
        try:
            self.attendance.log_action(self.user_display_name, action)
            self._update_punch_ui()
            
            # Send notification via main window
            host = self.window()
            if host and hasattr(host, "show_feedback"):
                host.show_feedback(f"Successfully Punched {action.upper()}", "success", 4000)
        except Exception as e:
            host = self.window()
            if host and hasattr(host, "show_feedback"):
                host.show_feedback(f"Punch failed: {e}", "error", 4000)
