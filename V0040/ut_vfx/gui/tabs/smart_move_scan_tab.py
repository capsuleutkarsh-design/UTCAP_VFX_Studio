import logging
from pathlib import Path
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QProgressBar,
    QTableWidget, QCheckBox, QComboBox, QGroupBox, QSlider,
    QFileDialog, QMessageBox, QSplitter, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer

from ut_vfx.core.infra.config_manager import ConfigManager
from ut_vfx.core.system.adaptation_engine import system_engine
from ut_vfx.core.domain.workers.smart_scan_worker import SmartScanWorker
from ut_vfx.utils.security import SecurityValidator
from ut_vfx.utils.text_utils import normalize_name, get_resolved_project_root
from ..dialogs.visual_diff_dialog import VisualDiffDialog

class SmartMoveScanTab(QWidget):
    """
    Smart Move Mean Tab with 'Incoming Delivery Mode'.
    Integrates Smart Ingest Intelligence.
    """

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.security_validator = SecurityValidator()
        self.is_move_scan_processing = False
        self.worker = None
        self._active_mode_type = None
        self._sp = system_engine.scale_px
        
        # UI State
        self.current_mode = "excel_based" # default

        self.setup_ui()
        self.apply_global_settings(self.config_manager.settings.get("global_settings", {}))
        # self.restore_last_paths() # Can implement later

    def _get_templates_map(self):
        templates = getattr(self.config_manager, "templates", None)
        if isinstance(templates, dict) and templates:
            return templates

        defaults = getattr(self.config_manager, "default_templates", {})
        return defaults if isinstance(defaults, dict) else {}

    def _extract_template_lists(self, template_info: Dict[str, Any]) -> tuple[list, list, list, list]:
        """Normalize template payload into flat folder lists."""
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
        """Apply global app settings relevant to this tab."""
        if not isinstance(global_settings, dict):
            return
        if hasattr(self, "dry_run_cb"):
            self.dry_run_cb.setChecked(bool(global_settings.get("dry_run_enabled", False)))

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left Panel (Controls)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right Panel (Logs)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        splitter.setSizes([self._sp(980, minimum=860), self._sp(860, minimum=760)])
        
        layout.addWidget(splitter)

    @staticmethod
    def _configure_form_layout(layout: QFormLayout):
        """Keep form rows stable and readable when the splitter resizes."""
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _create_browse_button(self, target_input: QLineEdit, mode: str = "dir"):
        """Create a browse button with a safe width so text never clips."""
        button = QPushButton("Browse")
        button.setMinimumWidth(self._sp(96, minimum=86))
        button.setMaximumWidth(self._sp(112, minimum=98))
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        if mode == "file":
            button.clicked.connect(lambda: self.browse_file(target_input))
        else:
            button.clicked.connect(lambda: self.browse_directory(target_input))
        return button

    def create_left_panel(self):
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # --- MODE SELECTION ---
        mode_group = QGroupBox("Operation Mode")
        mode_layout = QHBoxLayout()
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Standard Mode (Excel & Specific Shot)", 
            "Auto-Scan Mode (Client Drive Ingest)", 
            "Incoming Delivery Mode"
        ])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(QLabel("Select Mode:"))
        mode_layout.addWidget(self.mode_combo)
        
        mode_group.setLayout(mode_layout)
        left_layout.addWidget(mode_group)

        #Stack Layout for Swapping Modes
        self.mode_stack = QStackedWidget()
        
        # --- PAGE 1: STANDARD MODE (Original Move Scan Tab Layout) ---
        self.standard_page = QWidget()
        standard_layout = QVBoxLayout(self.standard_page)
        standard_layout.setContentsMargins(0, 0, 0, 0)
        
        self.excel_scan_card = self.create_excel_scan_card()
        standard_layout.addWidget(self.excel_scan_card)
        
        self.dest_card_std = self.create_destination_card()
        standard_layout.addWidget(self.dest_card_std)

        # Specific Shot Group (Checkable) - Back in Standard Mode
        self.specific_shot_group = self.create_specific_shot_group()
        standard_layout.addWidget(self.specific_shot_group)
        
        standard_action_layout = self.create_standard_action_layout()
        standard_layout.addLayout(standard_action_layout)
        
        standard_layout.addStretch()
        self.mode_stack.addWidget(self.standard_page)

        # --- PAGE 2: AUTO-SCAN MODE (From Folder Creator) ---
        self.autoscan_page = QWidget()
        autoscan_layout = QVBoxLayout(self.autoscan_page)
        autoscan_layout.setContentsMargins(0, 0, 0, 0)
        
        self.autoscan_card = self.create_autoscan_card()
        autoscan_layout.addWidget(self.autoscan_card)
        
        # Auto-Scan typically uses a Project Root destination
        self.dest_card_auto = self.create_destination_card()
        self.dest_card_auto.setTitle("Project Root (Target)")
        autoscan_layout.addWidget(self.dest_card_auto)
        
        autoscan_action_layout = self.create_autoscan_action_layout()
        autoscan_layout.addLayout(autoscan_action_layout)
        
        autoscan_layout.addStretch()
        self.mode_stack.addWidget(self.autoscan_page)

        # --- PAGE 3: INCOMING DELIVERY MODE ---
        self.incoming_page = QWidget()
        incoming_layout = QVBoxLayout(self.incoming_page)
        incoming_layout.setContentsMargins(0, 0, 0, 0)
        
        self.incoming_delivery_card = self.create_incoming_delivery_card()
        incoming_layout.addWidget(self.incoming_delivery_card)
        
        self.incoming_dest_card = self.create_destination_card()
        self.incoming_dest_card.setTitle("Project Root (Destination)")
        incoming_layout.addWidget(self.incoming_dest_card)
        
        # Project Settings for Incoming
        self.incoming_project_card = self.create_incoming_project_card()
        incoming_layout.addWidget(self.incoming_project_card)
        
        incoming_action_layout = self.create_incoming_action_layout()
        incoming_layout.addLayout(incoming_action_layout)
        
        incoming_layout.addStretch()
        self.mode_stack.addWidget(self.incoming_page)
        
        left_layout.addWidget(self.mode_stack)

        # --- SHARED SETTINGS (Bottom) ---
        self.settings_card = self.create_settings_card()
        left_layout.addWidget(self.settings_card)

        # Progress
        self.create_progress_area(left_layout)
        
        return left_widget

    def create_excel_scan_card(self):
        card = QGroupBox("Excel and Scan Directory")
        layout = QFormLayout(card)
        self._configure_form_layout(layout)

        self.excel_input = QLineEdit()
        self.excel_input.setPlaceholderText("Select Excel File")
        browse_excel = self._create_browse_button(self.excel_input, mode="file")
        
        excel_layout = QHBoxLayout()
        excel_layout.setSpacing(8)
        excel_layout.addWidget(self.excel_input)
        excel_layout.addWidget(browse_excel)
        layout.addRow("Excel File:", excel_layout)

        self.scan_dir_input = QLineEdit()
        self.scan_dir_input.setPlaceholderText("Select Scan Directory")
        browse_scan = self._create_browse_button(self.scan_dir_input)

        scan_layout = QHBoxLayout()
        scan_layout.setSpacing(8)
        scan_layout.addWidget(self.scan_dir_input)
        scan_layout.addWidget(browse_scan)
        layout.addRow("Scan Directory:", scan_layout)
        
        return card

    def create_destination_card(self):
        card = QGroupBox("Destination")
        layout = QFormLayout(card)
        self._configure_form_layout(layout)

        dest_input = QLineEdit()
        browse_btn = self._create_browse_button(dest_input)

        dest_layout = QHBoxLayout()
        dest_layout.setSpacing(8)
        dest_layout.addWidget(dest_input)
        dest_layout.addWidget(browse_btn)
        layout.addRow("Destination Root:", dest_layout)
        
        # Store referencing based on usage
        if not hasattr(self, 'dest_inputs'): self.dest_inputs = []
        self.dest_inputs.append(dest_input)
        
        # In Auto-Scan mode, we only check the Destination Root (Project Root) 
        # because the folder name is the project name
        if len(self.dest_inputs) == 2:  # Index 1 is the Auto-Scan destination
            dest_input.textChanged.connect(self.check_autoscan_project)

        return card

    def check_autoscan_project(self):
        """Check if target project folder (Destination Root) already exists for Auto-Scan."""
        if not hasattr(self, 'start_btn_auto') or len(self.dest_inputs) < 2:
            return
            
        dest = self.dest_inputs[1].text().strip()

        if not dest:
            self.start_btn_auto.setText("🚀 Start Auto-Scan")
            self.start_btn_auto.setStyleSheet("")
            return

        dest_path_obj = Path(dest)
        project_name = dest_path_obj.name
        resolved_root = get_resolved_project_root(dest, project_name)
        
        # In Auto-Scan, the target path we check is the resolved root + project name
        target_path = resolved_root / project_name
        exists = False

        if target_path.exists():
            exists = True

        if exists:
            self.start_btn_auto.setText("✅ Ingest to Existing Project")
            self.start_btn_auto.setStyleSheet(
                "background-color: #2a9d8f; color: white; font-weight: bold;"
            )
        else:
            self.start_btn_auto.setText("🆕 Create & Auto-Scan")
            self.start_btn_auto.setStyleSheet(
                "background-color: #e76f51; color: white; font-weight: bold;"
            )

    def create_specific_shot_group(self):
        group = QGroupBox("Specific Shot Move")
        group.setCheckable(True)
        group.setChecked(False)
        root_layout = QVBoxLayout(group)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        fields_widget = QWidget(group)
        layout = QFormLayout(fields_widget)
        self._configure_form_layout(layout)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def add_row(label_text: str, field_widget):
            lbl = QLabel(label_text)
            lbl.setMinimumWidth(self._sp(110, minimum=96))
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addRow(lbl, field_widget)

        self.specific_source_input = QLineEdit()
        browse_btn = self._create_browse_button(self.specific_source_input)
        
        source_layout = QHBoxLayout()
        source_layout.setSpacing(8)
        source_layout.addWidget(self.specific_source_input)
        source_layout.addWidget(browse_btn)
        add_row("Source Directory:", source_layout)

        self.specific_reel_input = QLineEdit()
        add_row("Reel Name:", self.specific_reel_input)

        self.specific_shot_input = QLineEdit()
        add_row("Shot Name:", self.specific_shot_input)

        self.specific_format_combo = QComboBox()
        self.specific_format_combo.addItems(["dpx", "exr", "tif", "mov", "jpg"])
        add_row("File Format:", self.specific_format_combo)

        root_layout.addWidget(fields_widget)
        fields_widget.setVisible(False)
        group.toggled.connect(fields_widget.setVisible)
        
        return group

    def create_autoscan_card(self):
        """BETA: Auto-Scan UI (from Folder Creator)"""
        card = QGroupBox("Auto-Scan Configuration")
        layout = QFormLayout(card)
        self._configure_form_layout(layout)
        
        # Source Drive/Folder
        self.autoscan_source_input = QLineEdit()
        self.autoscan_source_input.setPlaceholderText("Select Client/Incoming Drive")
        browse_btn = self._create_browse_button(self.autoscan_source_input)

        source_layout = QHBoxLayout()
        source_layout.setSpacing(8)
        source_layout.addWidget(self.autoscan_source_input)
        source_layout.addWidget(browse_btn)
        layout.addRow("Client Drive:", source_layout)
        
        # Target Reel (Optional)
        self.autoscan_reel_input = QLineEdit()
        self.autoscan_reel_input.setPlaceholderText("Optional: Enter Reel Name to enforce")
        layout.addRow("Target Reel:", self.autoscan_reel_input)
        
        layout.addRow(QLabel("ℹ️ Logic: Scans Drive > Finds Shots > Builds Structure > Moves Files"))
        
        return card

    def create_incoming_delivery_card(self):
        """Incoming Delivery UI — Smart Ingest Mode"""
        card = QGroupBox("Incoming Delivery")
        # Green border to highlight smart feature
        card.setStyleSheet("QGroupBox { border: 2px solid #4CAF50; border-radius: 5px; margin-top: 1ex; } QGroupBox::title { color: #4CAF50; }")
        layout = QFormLayout(card)
        self._configure_form_layout(layout)

        # Source Drive/Folder
        self.delivery_source_input = QLineEdit()
        self.delivery_source_input.setPlaceholderText("Select incoming drive or folder")
        browse_btn = self._create_browse_button(self.delivery_source_input)

        source_layout = QHBoxLayout()
        source_layout.setSpacing(8)
        source_layout.addWidget(self.delivery_source_input)
        source_layout.addWidget(browse_btn)
        layout.addRow("Incoming Path:", source_layout)

        # Confidence Threshold Slider
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(1, 100)
        self.confidence_slider.setValue(60) # Default 60%
        self.confidence_label = QLabel("Smart Confidence: 60%")
        self.confidence_slider.valueChanged.connect(self.update_confidence_label)
        
        # Initial call to set text
        self.update_confidence_label(60)
        
        layout.addRow(self.confidence_label, self.confidence_slider)

        # Category/Sorting Dropdown
        self.category_combo = QComboBox()
        self.category_combo.addItem("✨ Auto-Detect (Smart)", "auto")
        self.category_combo.addItem("⚠️ Quarantine Unmatched", "quarantine")
        self.category_combo.addItem("⬇️ Force All to '01_Scan'", "force_scan")
        # Add shot folders from config as forced targets
        templates = self._get_templates_map()
        _, _, _, shot_folders = self._extract_template_lists(templates.get("standard", {}))
        if not shot_folders:
            shot_folders = ["01_Plates", "07_Comp", "09_Render"]
        for folder in shot_folders:
            self.category_combo.addItem(f"📂 Force to '{folder}'", folder)
        self.category_combo.setCurrentIndex(0) # Default to Smart
        layout.addRow("Sorting Logic:", self.category_combo)

        layout.addRow(QLabel("ℹ️ Scans Drive → Detects Shots → Smart-Sorts Files → Builds Structure"))

        return card

    def create_incoming_project_card(self):
        """Project settings for Incoming Delivery mode."""
        card = QGroupBox("Project Settings")
        layout = QFormLayout(card)
        self._configure_form_layout(layout)

        # Project Name
        self.inc_project_input = QLineEdit()
        self.inc_project_input.setPlaceholderText("e.g. PROJ_001")
        # Debounce: 300ms delay so Path.iterdir() doesn't fire on every keystroke
        self._project_check_timer = QTimer(self)
        self._project_check_timer.setSingleShot(True)
        self._project_check_timer.setInterval(300)
        self._project_check_timer.timeout.connect(self.check_project_status)
        self.inc_project_input.textChanged.connect(lambda: self._project_check_timer.start())
        layout.addRow("Project Code:", self.inc_project_input)

        # Optional Reel Name
        self.inc_reel_input = QLineEdit()
        self.inc_reel_input.setPlaceholderText("Optional — leave blank for auto-detect")
        layout.addRow("Target Reel:", self.inc_reel_input)

        # Template selector
        self.inc_template_combo = QComboBox()
        templates = self._get_templates_map()
        if templates:
            self.inc_template_combo.addItems(list(templates.keys()))
        else:
            self.inc_template_combo.addItem("standard")
        layout.addRow("Template:", self.inc_template_combo)

        return card
    
    def check_project_status(self):
        """Check if project exists and update UI feedback."""
        project_code = self.inc_project_input.text().strip()
        # Destination root index 2 is for Incoming Delivery
        dest_root = self.dest_inputs[2].text().strip()
        
        if not project_code or not dest_root:
            self.start_btn_inc.setText("🚀 Smart Ingest & Build")
            self.start_btn_inc.setStyleSheet("") # Reset to default
            return

        # Sanitize code to match worker logic

        target_path = Path(dest_root) / project_code
        
        # Check if folder exists (using normalized check if needed, but direct first)
        exists = False
        if target_path.exists():
            exists = True
        else:
            # Check normalized match in parent
            try:
                if Path(dest_root).exists():
                    for child in Path(dest_root).iterdir():
                        if child.is_dir() and normalize_name(child.name) == normalize_name(project_code):
                            exists = True
                            break
            except Exception as exc:
                logging.debug("Project existence probe skipped for %s: %s", proj_dir, exc)

        if exists:
            self.start_btn_inc.setText("✅ Ingest to Existing Project")
            self.start_btn_inc.setStyleSheet("background-color: #2a9d8f; color: white; font-weight: bold;")
        else:
            self.start_btn_inc.setText("🆕 Create & Ingest")
            self.start_btn_inc.setStyleSheet("background-color: #e76f51; color: white; font-weight: bold;")

    def update_confidence_label(self, value):
        """Update label with descriptive text based on value."""
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
            
        self.confidence_label.setText(f"Smart Confidence: {value}% - {desc}")

    def create_settings_card(self):
        card = QGroupBox("Task Settings")
        layout = QVBoxLayout()
        self.dry_run_cb = QCheckBox("Dry Run (preview only)")
        self.overwrite_cb = QCheckBox("Overwrite existing files")
        self.fast_mode_cb = QCheckBox("Fast Mode (Skip Checksum)")
        layout.addWidget(self.overwrite_cb) # Match original order if possible
        layout.addWidget(self.dry_run_cb)
        layout.addWidget(self.fast_mode_cb)
        card.setLayout(layout)
        return card

    def create_standard_action_layout(self):
        layout = QHBoxLayout()
        self.read_excel_btn = QPushButton("Read Excel Data") # Original button
        # self.read_excel_btn.clicked.connect(...) # Implement reading logic if needed for beta
        
        self.start_btn_std = QPushButton("🚀 Start Move")
        self.start_btn_std.setObjectName("primaryButton")
        self.start_btn_std.clicked.connect(self.start_process_standard)
        
        self.stop_btn_std = QPushButton("🛑 Stop")
        self.stop_btn_std.setEnabled(False)
        self.stop_btn_std.clicked.connect(self.stop_process)
        
        layout.addWidget(self.read_excel_btn)
        layout.addWidget(self.start_btn_std)
        layout.addWidget(self.stop_btn_std)
        return layout

    def create_incoming_action_layout(self):
        layout = QHBoxLayout()
        self.start_btn_inc = QPushButton("🚀 Smart Ingest & Build")
        self.start_btn_inc.setObjectName("primaryButton")
        self.start_btn_inc.clicked.connect(self.start_process_incoming)
        
        self.pause_btn_inc = QPushButton("⏸️ Pause")
        self.pause_btn_inc.setEnabled(False)
        self.pause_btn_inc.clicked.connect(lambda: self.toggle_pause("incoming"))
        
        self.stop_btn_inc = QPushButton("🛑 Stop")
        self.stop_btn_inc.setEnabled(False)
        self.stop_btn_inc.clicked.connect(self.stop_process)
        
        layout.addWidget(self.start_btn_inc)
        layout.addWidget(self.pause_btn_inc)
        layout.addWidget(self.stop_btn_inc)
        return layout

    def create_progress_area(self, parent_layout):
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready")
        self.stats_label = QLabel("Files Moved: 0 | Folders Created: 0 | Files Skipped: 0 | Errors: 0")
        parent_layout.addWidget(self.progress_bar)
        parent_layout.addWidget(self.progress_label)
        parent_layout.addWidget(self.stats_label)

    def create_right_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Excel Preview (Only relevant for Standard Mode, but can keep visible or stack it)
        # For simplicity, let's keep it visible but maybe clear it if not in use?
        # Re-creating the original right panel structure
        preview_group = QGroupBox("Excel Data Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.excel_table = QTableWidget() # Simple mock for beta
        self.excel_table.setColumnCount(5)
        self.excel_table.setHorizontalHeaderLabels(["Reel", "Shot", "Status", "Matched Path", "Format"])
        preview_layout.addWidget(self.excel_table)
        
        layout.addWidget(preview_group)
        
        layout.addWidget(QLabel("Process Log:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        return widget

    def on_mode_changed(self, index):
        """Handle mode switching."""
        self.mode_stack.setCurrentIndex(index)
        
    def start_process_standard(self):
        """Start process for Standard Mode."""
        self.start_process(mode_type="standard")

    def create_autoscan_action_layout(self):
        layout = QHBoxLayout()
        self.start_btn_auto = QPushButton("🚀 Start Auto-Scan")
        self.start_btn_auto.setObjectName("primaryButton")
        self.start_btn_auto.clicked.connect(self.start_process_autoscan)
        
        self.pause_btn_auto = QPushButton("⏸️ Pause")
        self.pause_btn_auto.setEnabled(False)
        self.pause_btn_auto.clicked.connect(lambda: self.toggle_pause("autoscan"))
        
        self.stop_btn_auto = QPushButton("🛑 Stop")
        self.stop_btn_auto.setEnabled(False)
        self.stop_btn_auto.clicked.connect(self.stop_process)
        
        layout.addWidget(self.start_btn_auto)
        layout.addWidget(self.pause_btn_auto)
        layout.addWidget(self.stop_btn_auto)
        return layout

    def start_process_autoscan(self):
        """Start process for Auto-Scan Mode."""
        self.start_process(mode_type="autoscan")

    def start_process_incoming(self):
        """Start process for Incoming Delivery Mode."""
        self.start_process(mode_type="incoming")

    # --- HELPER METHODS ---

    def browse_directory(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            line_edit.setText(dir_path)

    def browse_file(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            "",
            "Excel Files (*.xlsx *.xls *.xlsm);;All Files (*)",
        )
        if file_path:
            line_edit.setText(file_path)

    def log_message(self, msg):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")

    def _get_template_data(self, template_name="standard"):
        """Build template_data tuple from config for SmartScanWorker."""
        templates = self._get_templates_map()
        t_data = templates.get(template_name, {})
        base_folders, production_subfolders, outsource_subfolders, shot_folders = self._extract_template_lists(t_data)
        if not shot_folders:
            shot_folders = ["01_Plates", "07_Comp", "09_Render"]

        return (
            base_folders or ["01_Scan", "05_Reels"],
            production_subfolders,
            outsource_subfolders,
            shot_folders,
        )

    def refresh_templates(self):
        """Refresh template-dependent dropdowns using shared ConfigManager state."""
        templates = self._get_templates_map()
        template_keys = list(templates.keys()) or ["standard"]

        if hasattr(self, "inc_template_combo"):
            current = self.inc_template_combo.currentText()
            self.inc_template_combo.blockSignals(True)
            self.inc_template_combo.clear()
            self.inc_template_combo.addItems(template_keys)
            if current and self.inc_template_combo.findText(current) >= 0:
                self.inc_template_combo.setCurrentText(current)
            self.inc_template_combo.blockSignals(False)

        if hasattr(self, "category_combo"):
            self.category_combo.blockSignals(True)
            self.category_combo.clear()
            self.category_combo.addItem("✨ Auto-Detect (Smart)", "auto")
            self.category_combo.addItem("⚠️ Quarantine Unmatched", "quarantine")
            self.category_combo.addItem("⬇️ Force All to '01_Scan'", "force_scan")
            _, _, _, shot_folders = self._extract_template_lists(templates.get("standard", {}))
            if not shot_folders:
                shot_folders = ["01_Plates", "07_Comp", "09_Render"]
            for folder in shot_folders:
                self.category_combo.addItem(f"📂 Force to '{folder}'", folder)
            self.category_combo.setCurrentIndex(0)
            self.category_combo.blockSignals(False)

    def start_process(self, mode_type):
        """Start SmartScanWorker with correct constructor API."""
        if self.is_move_scan_processing:
            return

        if mode_type == "incoming":
            worker = self._start_incoming()
        elif mode_type == "autoscan":
            worker = self._start_autoscan()
        elif mode_type == "standard":
            worker = self._start_standard()
        else:
            return

        if not worker:
            return

        self._cleanup_worker()
        self.worker = worker

        # --- Connect Signals (shared across all modes) ---
        self.worker.log_signal.connect(self.log_message)
        self.worker.progress_signal.connect(self._on_worker_progress)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.dry_run_data.connect(self.show_visual_diff)

        # CRASH SAFETY: QThread.finished fires even on crash
        self._active_mode_type = mode_type
        self.worker.finished.connect(self._on_worker_thread_done)

        self.is_move_scan_processing = True
        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting...")
        self.worker.start()

    def _cleanup_worker(self, timeout_ms=3000):
        worker = self.worker
        if not worker:
            return

        if worker.isRunning():
            stop = getattr(worker, "stop", None)
            if callable(stop):
                stop()
            else:
                worker.requestInterruption()
            worker.wait(timeout_ms)

        worker.deleteLater()
        if self.worker is worker:
            self.worker = None

    def _release_finished_worker(self, worker):
        if worker is not self.worker:
            return False
        self.worker = None
        worker.deleteLater()
        return True

    def _on_worker_progress(self, value, text):
        if self.sender() is not self.worker:
            return
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)

    def _on_worker_finished(self, success, reels, shots, folders, files_moved, msg):
        worker = self.sender()
        if not self._release_finished_worker(worker):
            return
        self.on_finished(success, msg, self._active_mode_type, reels, shots, folders, files_moved)

    def _shared_settings(self):
        """Gather shared worker settings from UI."""
        return {
            "dry_run": self.dry_run_cb.isChecked(),
            "overwrite": self.overwrite_cb.isChecked(),
            "fast_mode": self.fast_mode_cb.isChecked(),
        }

    def _start_incoming(self):
        """Start worker in Incoming Delivery mode."""
        s = self._shared_settings()
        source = self.delivery_source_input.text().strip()
        dest = self.dest_inputs[2].text().strip()
        project = self.inc_project_input.text().strip()
        reel = self.inc_reel_input.text().strip()
        template_name = self.inc_template_combo.currentText()

        # Smart Fix: Prevent Double Folder Creation
        if dest and project:
            resolved_root = get_resolved_project_root(dest, project)
            if str(resolved_root) != dest:
                dest = str(resolved_root)
                self.log_message(f"Smart Fix: Adjusted root to: {dest}")

        sorting_logic = self.category_combo.currentData() or "auto"

        if not source or not dest or not project:
            QMessageBox.warning(self, "Missing Info", "Source Path, Project Root, and Project Code are all required.")
            return None

        self.current_mode = "incoming_delivery"
        worker = SmartScanWorker(
            target_dir=dest, source_scan_path=source, project_name=project,
            template_data=self._get_template_data(template_name),
            target_reel_name=reel, confidence=self.confidence_slider.value() / 100.0,
            sorting_logic=sorting_logic, format_mapping=self.config_manager.format_mapping,
            **s
        )
        self.start_btn_inc.setEnabled(False)
        self.pause_btn_inc.setEnabled(True)
        self.stop_btn_inc.setEnabled(True)
        return worker

    def _start_autoscan(self):
        """Start worker in Auto-Scan mode."""
        s = self._shared_settings()
        source = self.autoscan_source_input.text().strip()
        dest = self.dest_inputs[1].text().strip()
        reel = self.autoscan_reel_input.text().strip()

        if not source or not dest:
            QMessageBox.warning(self, "Missing Info", "Client Drive and Destination Root are required.")
            return None

        self.current_mode = "autoscan"
        dest_path_obj = Path(dest)
        project_name = dest_path_obj.name
        resolved_root = get_resolved_project_root(dest, project_name)
        target_dir = str(resolved_root)
        self.log_message(f"Auto-Scan: Root='{target_dir}', Project='{project_name}'")

        worker = SmartScanWorker(
            target_dir=target_dir, source_scan_path=source, project_name=project_name,
            template_data=self._get_template_data("standard"),
            target_reel_name=reel, format_mapping=self.config_manager.format_mapping,
            **s
        )
        self.start_btn_auto.setEnabled(False)
        self.pause_btn_auto.setEnabled(True)
        self.stop_btn_auto.setEnabled(True)
        return worker

    def _start_standard(self):
        """Start worker in Standard mode."""
        s = self._shared_settings()
        dest = self.dest_inputs[0].text().strip()
        if not dest:
            QMessageBox.warning(self, "Error", "Destination root required")
            return None

        self.current_mode = "standard"
        source = ""
        reel = ""
        project_name = Path(dest).name

        if self.specific_shot_group.isChecked():
            source = self.specific_source_input.text().strip()
            reel = self.specific_reel_input.text().strip()
            if not source:
                QMessageBox.warning(self, "Error", "Source directory required for Specific Shot move.")
                return None

        worker = SmartScanWorker(
            target_dir=dest, source_scan_path=source if source else None,
            project_name=project_name, template_data=self._get_template_data("standard"),
            target_reel_name=reel, format_mapping=self.config_manager.format_mapping,
            **s
        )
        self.start_btn_std.setEnabled(False)
        self.stop_btn_std.setEnabled(True)
        return worker

    def show_visual_diff(self, operations):
        """Display the Visual Diff Dialog for Dry Run results."""
        if not operations:
            self.log_message("Dry Run: No operations generated.")
            return

        dlg = VisualDiffDialog(operations, self)
        if dlg.exec():
            self.log_message("User confirmed Dry Run. Uncheck 'Dry Run' to execute for real.")
            self.dry_run_cb.setChecked(False)
        else:
            self.log_message("Dry Run review cancelled.")

    def toggle_pause(self, mode_type):
        """Toggle pause/resume on the active worker."""
        if not self.worker:
            return
        
        # Determine which button to update
        btn = None
        if mode_type == "incoming":
            btn = self.pause_btn_inc
        elif mode_type == "autoscan":
            btn = self.pause_btn_auto
        
        if not btn:
            return
            
        if btn.text() == "⏸️ Pause":
            self.worker.pause()
            btn.setText("▶️ Resume")
            self.progress_label.setText("Paused")
        else:
            self.worker.resume()
            btn.setText("⏸️ Pause")
            self.progress_label.setText("Resuming...")

    def stop_process(self):
        """Send stop signal and reset UI."""
        if self.worker:
            stop = getattr(self.worker, "stop", None)
            if callable(stop):
                stop()
            else:
                self.worker.requestInterruption()
            self.log_message("🛑 Stop signal sent — waiting for current operation to finish...")

    def _on_worker_thread_done(self):
        """Crash-safety fallback: resets UI even if on_finished wasn't called."""
        worker = self.sender()
        if worker is not self.worker:
            return
        if self.is_move_scan_processing:
            # on_finished didn't fire — worker crashed
            self.log_message("⚠️ Worker thread ended unexpectedly.")
            self._reset_ui(self._active_mode_type)
        self._release_finished_worker(worker)

    def on_finished(self, success, msg, mode_type, reels=0, shots=0, folders=0, files_moved=0):
        """Handle worker completion."""
        self.is_move_scan_processing = False
        
        if success:
            self.stats_label.setText(
                f"Reels: {reels} | Shots: {shots} | Folders: {folders} | Files Moved: {files_moved}"
            )
            self.log_message(f"✅ {msg}")
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Done", f"Process Finished\n\n{msg}")
        else:
            self.log_message(f"❌ {msg}")
            QMessageBox.critical(self, "Error", msg)

        self._reset_ui(mode_type)

    def _reset_ui(self, mode_type):
        """Reset buttons for the given mode."""
        self.is_move_scan_processing = False
        self.progress_label.setText("Ready")
        self._active_mode_type = None
        
        if mode_type == "incoming":
            self.start_btn_inc.setEnabled(True)
            self.pause_btn_inc.setEnabled(False)
            self.pause_btn_inc.setText("⏸️ Pause")
            self.stop_btn_inc.setEnabled(False)
        elif mode_type == "standard":
            self.start_btn_std.setEnabled(True)
            self.stop_btn_std.setEnabled(False)
        elif mode_type == "autoscan":
            self.start_btn_auto.setEnabled(True)
            self.pause_btn_auto.setEnabled(False)
            self.pause_btn_auto.setText("⏸️ Pause")
            self.stop_btn_auto.setEnabled(False)

    def closeEvent(self, event):
        """Ensure background worker is stopped when tab closes."""
        self.stop_process()
        self._cleanup_worker(timeout_ms=2000)
        super().closeEvent(event)
