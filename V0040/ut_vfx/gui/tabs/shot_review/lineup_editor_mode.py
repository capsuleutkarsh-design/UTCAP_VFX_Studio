"""
Lineup Editor Mode (Olive Portal)
Acts as the bridge between UT_VFX and Olive Video Editor.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox, QListWidget,
    QListWidgetItem, QFrame, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from pathlib import Path
import logging
import subprocess
import datetime
import os
import shutil
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QTimer, QEvent

# Windows API Constants for Embedding
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
SWP_NOACTIVATE = 0x0010
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020

user32 = ctypes.windll.user32

from ....core.infra.config_manager import ConfigManager
from ....core.infra.global_config import GlobalConfig
from ....core.domain.review_shot import ShotStatus
from ....core.domain.olive_bridge import OliveBridge
import sys

logger = logging.getLogger(__name__)

def _get_process_name(pid: int) -> str:
    """Best-effort process executable name lookup for a PID."""
    if not pid:
        return ""
    try:
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        h_process = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
            False,
            int(pid),
        )
        if not h_process:
            return ""
        try:
            name_buff = ctypes.create_unicode_buffer(1024)
            ctypes.windll.psapi.GetModuleBaseNameW(h_process, 0, name_buff, 1024)
            return name_buff.value or ""
        finally:
            ctypes.windll.kernel32.CloseHandle(h_process)
    except Exception:
        return ""


def find_olive_window(target_pid: int = 0):
    """
    Find Olive window HWND using robust 3-tier matching:
    1) exact PID, 2) executable name, 3) title fallback.
    """
    found_hwnd = None
    this_pid = os.getpid()
    
    def callback(hwnd, _):
        nonlocal found_hwnd
        if not user32.IsWindowVisible(hwnd):
            return True

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        window_pid = int(pid.value)

        # Tier 1: direct PID match (strongest)
        if target_pid and window_pid == int(target_pid):
            found_hwnd = hwnd
            return False

        # Ignore this app's own windows.
        if window_pid == this_pid:
            return True

        # Tier 2: executable name
        exe_name = _get_process_name(window_pid).lower()
        if exe_name == "olive-editor.exe":
            found_hwnd = hwnd
            return False

        # Tier 3: conservative title fallback.
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.lower()
            if "olive" in title and "ut" not in title:
                found_hwnd = hwnd
                return False
        return True

    CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(CMPFUNC(callback), 0)
    return found_hwnd

class LineupEditorMode(QWidget):
    """
    Olive Portal - Manages synchronization with Olive 0.2
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.shots = []
        self.last_sync_time = None
        self.olive_process = None
        self.olive_hwnd = None
        self.embed_timer = None
        self.health_timer = None
        self.project_name = ""
        self.project_path = None
        self.prefer_proxy_media = True
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the Portal Dashboard"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Olive Container (The "Stage") -> Takes ALL space when active
        self.olive_container = QFrame()
        self.olive_container.setStyleSheet("background-color: #1e1e1e;")
        self.olive_container.hide()
        # Install event filter to catch resize events on the container
        self.olive_container.installEventFilter(self)
        layout.addWidget(self.olive_container, stretch=1)
        
        # 2. Main Dashboard (The "Lobby") -> Visible by default
        self.dashboard_widget = QWidget()
        self.setup_dashboard(self.dashboard_widget)
        layout.addWidget(self.dashboard_widget, stretch=0)
        
        # 3. Compact Toolbar (The "Active Mode") -> Hidden by default
        self.compact_toolbar = QWidget()
        self.compact_toolbar.hide()
        self.setup_compact_toolbar(self.compact_toolbar)
        layout.addWidget(self.compact_toolbar, stretch=0)

    def setup_dashboard(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header_group = QGroupBox("Olive Integration Bridge")
        header_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #444; margin-top: 10px; }")
        h_layout = QHBoxLayout(header_group)
        
        self.status_label = QLabel("Ready to Sync")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2A9D8F;")
        h_layout.addWidget(self.status_label)
        h_layout.addStretch()
        self.sync_time_label = QLabel("Last Sync: Never")
        h_layout.addWidget(self.sync_time_label)
        layout.addWidget(header_group)
        
        # Content
        content_layout = QHBoxLayout()
        
        # List
        list_group = QGroupBox("Approved Shots")
        l_layout = QVBoxLayout(list_group)
        self.shot_list = QListWidget()
        l_layout.addWidget(self.shot_list)
        content_layout.addWidget(list_group, stretch=2)
        
        # Actions
        action_group = QGroupBox("Actions")
        a_layout = QVBoxLayout(action_group)
        
        self.chk_prefer_proxy = QCheckBox("Prefer MP4 Proxy (Recommended)")
        self.chk_prefer_proxy.setChecked(self.prefer_proxy_media)
        self.chk_prefer_proxy.setToolTip(
            "Use MP4/MOV proxy media in Olive lineup when available for smoother playback."
        )
        self.chk_prefer_proxy.toggled.connect(self._on_prefer_proxy_toggled)
        a_layout.addWidget(self.chk_prefer_proxy)
        
        self.btn_sync = QPushButton("Sync to Olive")
        self.btn_sync.setMinimumHeight(50)
        self.btn_sync.setStyleSheet(self._get_btn_style("#E76F51"))
        self.btn_sync.clicked.connect(self.sync_lineup)
        a_layout.addWidget(self.btn_sync)
        
        self.btn_launch = QPushButton("Launch Olive Editor")
        self.btn_launch.setMinimumHeight(50)
        self.btn_launch.setStyleSheet(self._get_btn_style("#2A9D8F"))
        self.btn_launch.clicked.connect(self.launch_olive)
        a_layout.addWidget(self.btn_launch)
        
        a_layout.addStretch()
        content_layout.addWidget(action_group, stretch=1)
        
        layout.addLayout(content_layout)

    def setup_compact_toolbar(self, parent):
        """Slim bar shown when Olive is active"""
        parent.setStyleSheet("background-color: #2b2b2b; border-top: 2px solid #2A9D8F;")
        
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Status
        lbl = QLabel("Olive Active")
        lbl.setStyleSheet("font-weight: bold; color: #2A9D8F; font-size: 14px;")
        layout.addWidget(lbl)
        
        layout.addStretch()
        
        # Compact Actions
        btn_sync_mini = QPushButton("Re-Sync")
        btn_sync_mini.setToolTip("Generate new project file")
        btn_sync_mini.clicked.connect(self.sync_lineup)
        btn_sync_mini.setStyleSheet("background-color: #E76F51; color: white; border-radius: 4px; padding: 5px 15px; font-weight:bold;")
        layout.addWidget(btn_sync_mini)
        
        btn_close = QPushButton("Close / Expand")
        btn_close.clicked.connect(self.return_to_dashboard)
        btn_close.setStyleSheet("background-color: #444; color: white; border-radius: 4px; padding: 5px 15px;")
        layout.addWidget(btn_close)

    def return_to_dashboard(self):
        """Un-embed and show dashboard"""
        self._switch_to_dashboard_ui()
        
        reply = QMessageBox.question(self, "Close Session", "Stop Olive Editor process?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._stop_olive_process()

    def _switch_to_dashboard_ui(self):
        """Switch UI back to dashboard mode without process prompts."""
        self.olive_container.hide()
        self.compact_toolbar.hide()
        self.dashboard_widget.show()

    def _stop_olive_process(self, timeout_s: int = 3):
        """Gracefully stop Olive process with forced-kill fallback."""
        if self.embed_timer and self.embed_timer.isActive():
            self.embed_timer.stop()
        if self.health_timer and self.health_timer.isActive():
            self.health_timer.stop()

        proc = self.olive_process
        if not proc:
            return

        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=timeout_s)
                except subprocess.TimeoutExpired:
                    logger.warning("Olive process did not exit in %ss; killing.", timeout_s)
                    proc.kill()
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        logger.warning("Olive process kill wait timed out.")
        except Exception as exc:
            logger.warning("Failed to stop Olive process cleanly: %s", exc)
        finally:
            self.olive_process = None
            self.olive_hwnd = None

    
    def _find_olive_executable(self):
        """Find olive-editor.exe using config/env + robust path discovery."""
        
        candidates = []

        # 0) Config override (preferred)
        configured = GlobalConfig.get("olive_path")
        if configured:
            candidates.append(configured)

        # 1) Env override
        env_path = os.environ.get("OLIVE_EDITOR_PATH") or os.environ.get("OLIVE_EDITOR")
        if env_path:
            candidates.append(env_path)
        
        # 2) Detect if we're running from frozen exe or dev mode
        if getattr(sys, 'frozen', False):
            # Production mode - running from installed .exe
            base_dir = os.path.dirname(sys.executable)
            
            # 1. Pyinstaller --onedir (v6+) usually puts bundled data in _internal/
            candidates.append(os.path.join(base_dir, "_internal", "olive-editor", "olive-editor.exe"))
            
            # 2. Pyinstaller --onefile uses _MEIPASS
            if hasattr(sys, '_MEIPASS'):
                candidates.append(os.path.join(sys._MEIPASS, "olive-editor", "olive-editor.exe"))
                
            # 3. Direct relative
            candidates.append(os.path.join(base_dir, "olive-editor", "olive-editor.exe"))
            candidates.append(os.path.join(base_dir, "..", "olive-editor", "olive-editor.exe"))
        else:
            # Dev mode - running from .py
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # file: .../ut_vfx/gui/tabs/shot_review/lineup_editor_mode.py
            # project root: .../V0040
            module_root = Path(__file__).resolve().parents[3]  # .../ut_vfx
            project_root = module_root.parent
            candidates.extend(
                [
                    str(project_root / "external" / "olive-editor" / "olive-editor.exe"),
                    str(module_root / "external" / "olive-editor" / "olive-editor.exe"),
                    str(project_root / "olive-editor" / "olive-editor.exe"),
                ]
            )
        
        # 3) AppData and local install fallbacks
        candidates.append(str(Path.home() / "AppData/Local/UT_VFX Production/olive-editor/olive-editor.exe"))
        candidates.append(str(Path.home() / "AppData/Local/UTVFX/olive-editor/olive-editor.exe"))
        candidates.append(str(Path.cwd() / "olive-editor" / "olive-editor.exe"))

        # 4) PATH lookup
        system_path = shutil.which("olive-editor") or shutil.which("olive-editor.exe")
        if system_path:
            candidates.append(system_path)
        
        for candidate in candidates:
            candidate_path = Path(candidate)
            if candidate_path.exists():
                logger.info(f"Found Olive at: {candidate_path}")
                return candidate_path
        
        logger.error(f"Olive not found. Tried: {candidates}")
        return None
        
    def _get_btn_style(self, color):
        hover_color = QColor(color).lighter(112).name() if QColor(color).isValid() else color
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
                border: 2px solid {color};
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                border: 2px solid white;
            }}
        """

    def set_project_context(self, project_name: str = "", project_path: Path = None):
        """Set active project context so lineup output is project-scoped."""
        self.project_name = (project_name or "").strip()
        self.project_path = project_path

    def _on_prefer_proxy_toggled(self, checked: bool):
        """Switch between proxy-preferred and original-source media sync."""
        self.prefer_proxy_media = bool(checked)

    def _infer_project_name(self) -> str:
        """Best-effort project name inference from context or shots."""
        if self.project_name:
            return self.project_name

        if self.project_path:
            try:
                return Path(self.project_path).name
            except Exception as exc:
                logger.debug("Failed to derive project code from project_path: %s", exc)

        for shot in self.shots:
            shot_project = getattr(shot, "project_name", "") or ""
            if shot_project:
                return shot_project

        return "Unknown_Project"

    def _sanitize_project_key(self, name: str) -> str:
        """Filesystem-safe project folder key."""
        clean = "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in (name or "").strip())
        clean = clean.strip("._ ")
        return clean or "Unknown_Project"

    def set_shots(self, all_shots: list):
        """Update list with approved shots"""
        self.shots = all_shots
        self.shot_list.clear()
        
        approved = [s for s in all_shots if s.status == ShotStatus.APPROVED]
        
        if not approved:
            item = QListWidgetItem("No approved shots found.")
            item.setFlags(Qt.NoItemFlags)
            self.shot_list.addItem(item)
            self.btn_sync.setEnabled(False)
            return
            
        self.btn_sync.setEnabled(True)
        
        for shot in approved:
            icon = "-"
            has_scan = "Scan: YES" if shot.has_scan() else "Scan: NO"
            has_render = "Render: YES" if shot.has_render() else "Render: NO"
            
            text = f"{icon} {shot.name}  |  {has_scan}  |  {has_render}"
            item = QListWidgetItem(text)
            self.shot_list.addItem(item)

        project_label = self._infer_project_name()
        self.status_label.setText(f"{len(approved)} Shots Ready to Sync ({project_label})")

    def sync_lineup(self):
        """Generate the .ovexml file"""
        try:
            config = ConfigManager()
            base_dir = config.get_path("central_library")
            if not base_dir.exists():
                try:
                    base_dir.mkdir(parents=True, exist_ok=True)
                except OSError:
                    # Fallback
                    base_dir = Path.home() / "RuntimeData" / "UT_VFX_Lineups"
                    base_dir.mkdir(parents=True, exist_ok=True)

            project_name = self._infer_project_name()
            project_key = self._sanitize_project_key(project_name)
            project_dir = base_dir / "Lineups" / project_key
            project_dir.mkdir(parents=True, exist_ok=True)
            self.output_path = project_dir / "Current_Lineup.ovexml"
            
            bridge = OliveBridge()
            approved_shots = [s for s in self.shots if s.status == ShotStatus.APPROVED]
            
            if not approved_shots:
                QMessageBox.warning(self, "No Shots", "No approved shots to sync.")
                return

            if bridge.generate_project(
                approved_shots,
                self.output_path,
                prefer_proxy_media=self.prefer_proxy_media
            ):
                self.last_sync_time = datetime.datetime.now()
                self.sync_time_label.setText(f"Last Sync: {self.last_sync_time.strftime('%H:%M:%S')}")
                
                QMessageBox.information(
                    self, 
                    "Sync Complete", 
                    f"Project: {project_name}\nGenerated: {self.output_path.name}\n\n"
                    f"Path: {self.output_path}\nMedia Mode: {'Prefer MP4 Proxy' if self.prefer_proxy_media else 'Original Sources'}\n\n"
                    "You can now Launch Olive."
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to generate project file.")
                
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            QMessageBox.critical(self, "Sync Error", str(e))

    def launch_olive(self):
        """Find and Launch Olive Editor in EMBEDDED Mode"""
        try:
            # 1. Find Executable using dynamic path detection
            base_path = self._find_olive_executable()

            if not base_path or not base_path.exists():
                QMessageBox.warning(
                    self,
                    "Olive Not Found",
                    f"Could not find Olive executable at:\n{base_path}\n\n"
                    f"Expected location: {Path.home() / 'AppData' / 'Local' / 'UT_VFX Production' / 'olive-editor' / 'olive-editor.exe'}"
                )
                return

            # 2. Kill stale instances to avoid attaching to a ghost
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "olive-editor.exe"],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except Exception:
                pass

            # 3. Sanitize environment — prevent parent Qt DLLs from
            #    conflicting with Olive's own Qt build.
            env = os.environ.copy()
            for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
                        "QT_FONTS_PATH", "PYTHONPATH", "PYTHONHOME"):
                env.pop(key, None)

            # 4. Launch Process
            args = [str(base_path)]
            if hasattr(self, 'output_path') and self.output_path.exists():
                args.append(str(self.output_path))

            logger.info("Launching Olive: %s", args)
            self.olive_process = subprocess.Popen(args, cwd=base_path.parent, env=env)

            # 5. Start Embedding Sequence
            self.status_label.setText("Waiting for Olive...")
            self.embed_attempts = 0
            self.embed_timer = QTimer(self)
            self.embed_timer.timeout.connect(self.try_embed_olive)
            self.embed_timer.start(500)  # Check every 500ms

            # Switch to Compact Mode to optimize space
            self.dashboard_widget.hide()
            self.compact_toolbar.show()
            self.olive_container.show()

        except Exception as e:
            logger.error(f"Launch failed: {e}")
            QMessageBox.critical(self, "Launch Error", str(e))

    def try_embed_olive(self):
        """Poll for Olive window and capture it"""
        self.embed_attempts += 1

        # Fast-fail: process already exited (crash/DLL error)
        if self.olive_process and self.olive_process.poll() is not None:
            rc = self.olive_process.returncode
            self.embed_timer.stop()
            logger.error("Olive exited during startup (code %s)", rc)
            self.status_label.setText(f"Olive crashed (exit {rc})")
            self.olive_process = None
            self._switch_to_dashboard_ui()
            QMessageBox.warning(
                self, "Olive Error",
                f"Olive Editor exited unexpectedly (code {rc}).\n\n"
                "This usually means a DLL conflict or missing dependency.\n"
                "Try launching again or check the Olive logs.",
            )
            return

        if self.embed_attempts > 20:  # 10s timeout
            self.embed_timer.stop()
            self.status_label.setText("Embedding Timed Out")
            return

        if not self.olive_process:
            self.embed_timer.stop()
            return

        # Try robust window lookup (PID first).
        hwnd = find_olive_window(target_pid=self.olive_process.pid if self.olive_process else 0)
        if hwnd:
            self.embed_window(hwnd)
            self.embed_timer.stop()
            self.status_label.setText("Olive Embedded")
            self._start_health_monitor()

    def _start_health_monitor(self):
        """Watch Olive process after successful embed and surface crash state to user."""
        if self.health_timer and self.health_timer.isActive():
            self.health_timer.stop()
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._check_olive_health)
        self.health_timer.start(2000)

    def _check_olive_health(self):
        proc = self.olive_process
        if not proc:
            return
        rc = proc.poll()
        if rc is None:
            return
        if self.health_timer and self.health_timer.isActive():
            self.health_timer.stop()
        self.status_label.setText(f"Olive exited (code {rc})")
        self.olive_process = None
        self.olive_hwnd = None
        self._switch_to_dashboard_ui()
        QMessageBox.warning(
            self,
            "Olive Exited",
            f"Olive process exited with code {rc}.",
        )
            
    def embed_window(self, hwnd):
        """Perform Windows API magic to swallow the window"""
        self.olive_hwnd = hwnd
        
        # 1. Reparent to our container
        container_hwnd = int(self.olive_container.winId())
        user32.SetParent(hwnd, container_hwnd)
        
        # 2. Remove Title Bar & Borders (Make it look like a child widget)
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style = style & ~WS_CAPTION & ~WS_THICKFRAME | WS_CHILD
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        
        # 3. Trigger Style Update
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FRAMECHANGED | SWP_NOACTIVATE | SWP_NOZORDER)
        
        # 4. Initial Resize
        self.resize_embedded()
        
    def eventFilter(self, obj, event):
        """Watch for container resize events"""
        if obj == self.olive_container and event.type() == QEvent.Resize:
            self.resize_embedded()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        """Handle main window resize -> resize Olive"""
        super().resizeEvent(event)
        self.resize_embedded()
        
    def resize_embedded(self):
        """Force Olive window to fill the container (Handling DPI)"""
        if self.olive_hwnd and self.olive_container.isVisible():
            # Get Scaling Factor (DPI)
            dpr = self.olive_container.devicePixelRatio()
            
            # Qt Size (Logical) -> Windows API Size (Physical)
            width = int(self.olive_container.width() * dpr)
            height = int(self.olive_container.height() * dpr)
            
            # Reparented windows use coordinates relative to parent's client area.
            # However, if the parent (QT widget) is also scaled, we might need to be careful?
            # Usually SetParent places it in client area (0,0).
            
            # Debug log (optional, but good for checking)
            # logger.info(f"Resizing Embedded: Logical={self.olive_container.width()}x{self.olive_container.height()}, DPR={dpr}, Physical={width}x{height}")
            
            user32.MoveWindow(self.olive_hwnd, 0, 0, width, height, True)
    
    def closeEvent(self, event):
        """Clean up process on close"""
        if hasattr(self, "embed_timer") and self.embed_timer.isActive():
            self.embed_timer.stop()
        if self.health_timer and self.health_timer.isActive():
            self.health_timer.stop()
        self._stop_olive_process()
        super().closeEvent(event)
