"""
Incoming Delivery Tab — Final Version.
Reconstructed from pyc bytecode analysis and smart_move_scan_tab reference.

Dedicated tab for the Incoming Delivery workflow mode:
- Smart Ingest engine (SmartScanWorker)
- Confidence slider with descriptive labels
- Auto-detect category vs forced sort logic
- Typing-debounce + existing project detection
- Settings: Dry Run, Overwrite, Fast Mode
- apply_global_settings support
"""

import logging
from pathlib import Path
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QProgressBar,
    QGroupBox, QCheckBox, QComboBox, QSlider, QSplitter,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer

from ut_vfx.core.infra.config_manager import ConfigManager
from ut_vfx.core.domain.workers.smart_scan_worker import SmartScanWorker
from ut_vfx.utils.security import SecurityValidator
from ut_vfx.utils.text_utils import normalize_name, get_resolved_project_root


class IncomingDeliveryTab(QWidget):
    """
    Incoming Delivery Tab — Dedicated single-tab workflow for receiving
    client deliveries and ingesting them using Smart Ingest logic.

    Features:
    - Auto-detects shots and classifies files by context
    - Confidence slider to control matching strictness
    - Category/sorting override options
    - Checks for existing projects before running
    - Dry-run, overwrite, and fast-mode toggles
    """

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.security_validator = SecurityValidator()
        self.is_processing = False
        self.worker = None

        # Debounce timer for project name field
        self._project_check_timer = QTimer(self)
        self._project_check_timer.setSingleShot(True)
        self._project_check_timer.setInterval(350)
        self._project_check_timer.timeout.connect(self.check_existing_project)

        self.setup_ui()
        self.apply_global_settings(
            self.config_manager.settings.get("global_settings", {})
        )

    def _cleanup_worker(self, timeout_ms: int = 3000):
        worker = self.worker
        if worker is None:
            return
        if worker.isRunning():
            worker.is_running = False
            worker.requestInterruption()
            worker.wait(timeout_ms)
        try:
            worker.deleteLater()
        except RuntimeError as exc:
            logging.debug("Incoming delivery worker deleteLater skipped: %s", exc)
        self.worker = None

    def _on_worker_thread_finished(self):
        if self.sender() is self.worker:
            self.worker = None

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _get_templates_map(self) -> dict:
        templates = getattr(self.config_manager, "templates", None)
        if isinstance(templates, dict) and templates:
            return templates
        defaults = getattr(self.config_manager, "default_templates", {})
        return defaults if isinstance(defaults, dict) else {}

    def _extract_template_lists(self, template_info: Dict[str, Any]) -> tuple[list, list, list, list]:
        """
        Normalize template payload into flat folder lists.

        Supports both:
        - Flat schema: template["shot_folders"]
        - Nested schema: template["structure"]["shot_folders"]
        """
        if not isinstance(template_info, dict):
            return [], [], [], []

        structure = template_info.get("structure")
        source = structure if isinstance(structure, dict) else template_info

        def _safe_list(key: str) -> list:
            value = source.get(key, [])
            return value if isinstance(value, list) else []

        return (
            _safe_list("base_folders"),
            _safe_list("production_subfolders"),
            _safe_list("outsource_subfolders"),
            _safe_list("shot_folders"),
        )

    def apply_global_settings(self, global_settings: Dict[str, Any]):
        """Respond to global app settings (e.g. dark mode, default dry-run)."""
        if not isinstance(global_settings, dict):
            return
        if hasattr(self, "dry_run_cb"):
            self.dry_run_cb.setChecked(
                bool(global_settings.get("dry_run_enabled", False))
            )

    def start_typing_timer(self):
        """Restart the debounce timer on every keystroke (avoids I/O on each key)."""
        self._project_check_timer.start()

    # ── UI Construction ──────────────────────────────────────────────────────

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        layout.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        left = QWidget()
        layout = QVBoxLayout(left)

        layout.addWidget(self._build_incoming_card())
        layout.addWidget(self._build_project_card())
        layout.addWidget(self._build_settings_card())
        layout.addLayout(self._build_action_layout())
        layout.addWidget(self._build_progress_area())
        layout.addStretch()

        return left

    def _build_incoming_card(self) -> QGroupBox:
        """Incoming drive / confidence / sorting options."""
        card = QGroupBox("Incoming Media Configuration")
        card.setStyleSheet(
            "QGroupBox { border: 2px solid #4CAF50; border-radius: 5px; margin-top: 1ex; }"
            "QGroupBox::title { color: #4CAF50; }"
        )
        form = QFormLayout(card)

        # Source path
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Select incoming client drive or folder...")
        browse_src = QPushButton("Browse")
        browse_src.clicked.connect(lambda: self.browse_dir(self.source_input))
        src_row = QHBoxLayout()
        src_row.addWidget(self.source_input)
        src_row.addWidget(browse_src)
        form.addRow("Client Drive / Path:", src_row)

        # Confidence slider
        self.confidence_label = QLabel("Smart Confidence: 60% — Balanced")
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(1, 100)
        self.confidence_slider.setValue(60)
        self.confidence_slider.valueChanged.connect(self.update_confidence_label)
        self.update_confidence_label(60)
        form.addRow(self.confidence_label, self.confidence_slider)

        # Category/sorting override
        self.category_combo = QComboBox()
        self.category_combo.addItem("✨ Auto-Detect (Smart)", "auto")
        self.category_combo.addItem("⚠️ Quarantine Unmatched", "quarantine")
        self.category_combo.addItem("⬇️ Force All to '01_Scan'", "force_scan")
        templates = self._get_templates_map()
        _, _, _, shot_folders = self._extract_template_lists(templates.get("standard", {}))
        if not shot_folders:
            shot_folders = ["01_Plates", "07_Comp", "09_Render"]
        for folder in shot_folders:
            self.category_combo.addItem(f"📂 Force to '{folder}'", folder)
        self.category_combo.currentIndexChanged.connect(self.update_category_options)
        form.addRow("Sorting Logic:", self.category_combo)

        form.addRow(QLabel(
            "ℹ️  Scans Drive → Detects Shots → Smart-Sorts Files → Builds Structure"
        ))

        return card

    def _build_project_card(self) -> QGroupBox:
        """Project code + destination root + reel + template."""
        card = QGroupBox("Project Settings")
        form = QFormLayout(card)

        # Project code (with typing debounce → check_existing_project)
        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("e.g. PROJ_001")
        self.project_input.textChanged.connect(self.start_typing_timer)
        form.addRow("Project Code:", self.project_input)

        # Destination root
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("Root folder where the project will be created")
        self.dest_input.textChanged.connect(self.start_typing_timer)
        browse_dest = QPushButton("Browse")
        browse_dest.clicked.connect(lambda: self.browse_dir(self.dest_input))
        dest_row = QHBoxLayout()
        dest_row.addWidget(self.dest_input)
        dest_row.addWidget(browse_dest)
        form.addRow("Destination Root:", dest_row)

        # Optional reel
        self.reel_input = QLineEdit()
        self.reel_input.setPlaceholderText("Optional — leave blank for auto-detect")
        form.addRow("Target Reel:", self.reel_input)

        # Template
        self.template_combo = QComboBox()
        templates = self._get_templates_map()
        if templates:
            self.template_combo.addItems(list(templates.keys()))
        else:
            self.template_combo.addItem("standard")
        form.addRow("Pipeline Template:", self.template_combo)

        return card

    def _build_settings_card(self) -> QGroupBox:
        card = QGroupBox("Task Settings")
        row = QHBoxLayout(card)
        self.dry_run_cb = QCheckBox("Dry Run (preview only)")
        self.overwrite_cb = QCheckBox("Overwrite existing files")
        self.fast_mode_cb = QCheckBox("⚡ Fast Mode (skip checksum)")
        row.addWidget(self.dry_run_cb)
        row.addWidget(self.overwrite_cb)
        row.addWidget(self.fast_mode_cb)
        return card

    def _build_action_layout(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.run_btn = QPushButton("🚀 Smart Ingest & Build")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.clicked.connect(self.run_process)

        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_process)

        row.addWidget(self.run_btn)
        row.addWidget(self.stop_btn)
        return row

    def _build_progress_area(self) -> QWidget:
        widget = QWidget()
        col = QVBoxLayout(widget)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.status_label = QLabel("Ready")
        self.stats_label = QLabel("Files Moved: 0 | Folders Created: 0 | Skipped: 0 | Errors: 0")
        self.stats_label.setStyleSheet("color: #888; font-size: 11px;")
        col.addWidget(self.progress_bar)
        col.addWidget(self.status_label)
        col.addWidget(self.stats_label)
        return widget

    def _build_right_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Process Log:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        return widget

    # ── Logic / Slots ────────────────────────────────────────────────────────

    def browse_dir(self, field: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Select Directory")
        if d:
            field.setText(d)

    def update_confidence_label(self, value: int):
        """Show a descriptive label next to the confidence slider."""
        if value >= 90:
            desc = "Strict (Exact Names Only)"
        elif value >= 70:
            desc = "High (Names & Context)"
        elif value >= 50:
            desc = "Balanced (Extensions Allowed)"
        elif value >= 30:
            desc = "Loose (Aggressive Matching)"
        else:
            desc = "Unsafe (Everything Goes)"
        self.confidence_label.setText(f"Smart Confidence: {value}% — {desc}")

    def update_category_options(self, index: int):
        """Respond when the sorting logic dropdown changes."""
        # Future: could enable/disable other options based on selection
        logging.debug(f"[IncomingDelivery] Sorting mode changed to index {index}")

    def check_existing_project(self):
        """Check if target project folder already exists, update button label."""
        project = self.project_input.text().strip()
        dest = self.dest_input.text().strip()

        if not project or not dest:
            self.run_btn.setText("🚀 Smart Ingest & Build")
            self.run_btn.setStyleSheet("")
            return

        resolved_root = get_resolved_project_root(dest, project)
        target_path = resolved_root / project
        exists = False

        if target_path.exists():
            exists = True
        else:
            try:
                dest_path = Path(dest)
                if dest_path.exists():
                    for child in dest_path.iterdir():
                        if child.is_dir() and normalize_name(child.name) == normalize_name(project):
                            exists = True
                            break
            except Exception as exc:
                logging.debug("Project existence probe skipped for %s: %s", proj_dir, exc)

        if exists:
            self.run_btn.setText("✅ Ingest to Existing Project")
            self.run_btn.setStyleSheet(
                "background-color: #2a9d8f; color: white; font-weight: bold;"
            )
        else:
            self.run_btn.setText("🆕 Create & Ingest")
            self.run_btn.setStyleSheet(
                "background-color: #e76f51; color: white; font-weight: bold;"
            )

    def run_process(self):
        if self.is_processing:
            return

        project = self.project_input.text().strip()
        dest = self.dest_input.text().strip()
        source = self.source_input.text().strip()
        template_name = self.template_combo.currentText()
        reel = self.reel_input.text().strip()
        confidence = self.confidence_slider.value() / 100.0
        sorting_logic = self.category_combo.currentData() or "auto"

        if not all([project, dest, source]):
            QMessageBox.warning(self, "Missing Info", "Please fill in Project Code, Destination Root, and Client Drive.")
            return

        # Validate paths
        is_valid_src, err_src = self.security_validator.validate_directory_path(Path(source))
        if not is_valid_src:
            QMessageBox.critical(self, "Security Error", f"Source Client Drive validation failed: {err_src}")
            return

        is_valid_dest, err_dest = self.security_validator.validate_directory_path(Path(dest), must_exist=True)
        if not is_valid_dest:
            QMessageBox.critical(self, "Security Error", f"Destination Root validation failed: {err_dest}")
            return

        # Build template tuple
        templates = self._get_templates_map()
        t_data = templates.get(template_name, {})
        base_folders, production_subfolders, outsource_subfolders, shot_folders = self._extract_template_lists(t_data)
        if not shot_folders:
            logging.warning(
                "[IncomingDelivery] Template '%s' resolved with empty shot_folders; using safe defaults.",
                template_name,
            )
            shot_folders = ["01_Scan", "07_Comp", "08_Output"]
        template_tuple = (
            base_folders,
            production_subfolders,
            outsource_subfolders,
            shot_folders,
        )
        
        resolved_root = get_resolved_project_root(dest, project)
        self._cleanup_worker()

        self.worker = SmartScanWorker(
            target_dir=resolved_root,
            source_scan_path=Path(source),
            project_name=project,
            template_data=template_tuple,
            target_reel_name=reel,
            overwrite=self.overwrite_cb.isChecked(),
            dry_run=self.dry_run_cb.isChecked(),
            fast_mode=self.fast_mode_cb.isChecked(),
            confidence=confidence,
            sorting_logic=sorting_logic,
        )

        self.worker.log_signal.connect(self.log_message)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.finished.connect(self._on_worker_thread_finished)
        self.worker.finished.connect(self.worker.deleteLater)

        self.is_processing = True
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.worker.start()

    def stop_process(self):
        if self.worker:
            self.worker.is_running = False
            self.worker.requestInterruption()
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Stopping...")

    def log_message(self, msg: str):
        self.log_text.append(msg)

    def _on_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_finished(self, success, files_moved, folders_created, files_skipped, errors, summary_msg):
        if self.sender() is not self.worker:
            return
        self.is_processing = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stats_label.setText(
            f"Files Moved: {files_moved} | Folders Created: {folders_created} "
            f"| Skipped: {files_skipped} | Errors: {errors}"
        )
        self.log_message(f"\n{'✅' if success else '❌'} Finished: {summary_msg}")
        if success:
            QMessageBox.information(self, "Done", f"Ingest completed.\n\n{summary_msg}")
        else:
            QMessageBox.warning(self, "Finished with Errors", summary_msg)

        # Reset button label
        self.run_btn.setText("🚀 Smart Ingest & Build")
        self.run_btn.setStyleSheet("")

    # ── Thread cleanup ───────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Ensure the worker thread is cleanly stopped when the tab closes."""
        self._project_check_timer.stop()
        self._cleanup_worker(timeout_ms=3000)
        super().closeEvent(event)
