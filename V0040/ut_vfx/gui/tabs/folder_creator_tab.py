from pathlib import Path
from typing import Dict, Any, Tuple
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QProgressBar,
    QCheckBox, QComboBox, QGroupBox,
    QFileDialog, QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem, QDialog
)
from PySide6.QtCore import Qt, Signal, QTimer

from ...core.infra.config_manager import ConfigManager
from ...core.worker_threads import FolderCreationWorker
from ...core.domain.workers.excel_loader import ExcelLoadWorker
from ...utils.security import SecurityValidator, SecurityError
from ...utils.text_utils import get_resolved_project_root

# Import design tokens for theming
from ...core.infra.design_tokens import ColorTokens as C, TypographyTokens as T
from ...gui.dialogs.custom_template_dialog import CustomTemplateDialog



class FolderCreatorTab(QWidget):
    """SECURE Tab for creating folder structures with Excel or Scan modes."""

    # Signal to notify other tabs about template changes
    template_changed = Signal(dict)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.format_mapping = self.config_manager.format_mapping
        self.is_processing = False
        self.folder_creation_thread = None
        self.excel_worker = None
        self.security_validator = SecurityValidator()
        self.folder_preview_tree = None
        self.current_mode = "excel" # Default mode

        self.setup_ui()
        self.load_templates_to_ui()
        self.restore_last_paths()
        self.apply_global_settings(self.config_manager.settings.get("global_settings", {}))

    def apply_global_settings(self, global_settings: Dict[str, Any]):
        """Apply global app settings relevant to this tab."""
        if not isinstance(global_settings, dict):
            return
        if hasattr(self, "dry_run_cb"):
            self.dry_run_cb.setChecked(bool(global_settings.get("dry_run_enabled", False)))

    def _extract_template_lists(self, template_info: Dict[str, Any]) -> Tuple[list, list, list, list]:
        """
        Normalize template schema to flat folder lists.

        Supports both:
        - Flat config schema: template['base_folders']
        - Nested schema: template['structure']['base_folders']
        """
        if not isinstance(template_info, dict):
            return [], [], [], []

        structure = template_info.get("structure")
        source = structure if isinstance(structure, dict) else template_info

        def _safe_list(key: str) -> list:
            value = source.get(key, [])
            return value if isinstance(value, list) else []

        base_folders = _safe_list("base_folders")
        production_subfolders = _safe_list("production_subfolders")
        outsource_subfolders = _safe_list("outsource_subfolders")
        shot_folders = _safe_list("shot_folders")

        return base_folders, production_subfolders, outsource_subfolders, shot_folders

    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel - Preview and logs
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 4) # 40% Control Panel
        splitter.setStretchFactor(1, 6) # 60% Logs/Preview
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        layout.addWidget(splitter)

    def create_left_panel(self):
        """Create the left panel with controls."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        # 1. Project Settings
        self.project_card = QGroupBox("Project Settings")
        project_layout = QFormLayout(self.project_card)
        
        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("Enter Project Code / Name (e.g. PRJ_001)")
        
        project_layout.addRow("Project Code:", self.project_name_input)

        project_dir_layout = QHBoxLayout()
        self.project_dir_input = QLineEdit()
        self.project_dir_input.setReadOnly(True)
        
        # Debounce timer for status check
        self.typing_timer = QTimer()
        self.typing_timer.setSingleShot(True)
        self.typing_timer.setInterval(500) # 500ms delay
        self.typing_timer.timeout.connect(self.check_destination_status)

        # Connect signals to timer
        self.project_name_input.textChanged.connect(self.start_typing_timer)
        self.project_dir_input.textChanged.connect(self.start_typing_timer)

        browse_project_btn = QPushButton("Browse")
        browse_project_btn.clicked.connect(self.browse_project_directory)
        project_dir_layout.addWidget(self.project_dir_input)
        project_dir_layout.addWidget(browse_project_btn)
        project_layout.addRow("Target Root:", project_dir_layout)
        left_layout.addWidget(self.project_card)

        # 2. Template Selection
        template_card = QGroupBox("Template Configuration")
        template_layout = QVBoxLayout(template_card)
        combo_layout = QHBoxLayout()
        self.template_combo = QComboBox()
        combo_layout.addWidget(QLabel("Pipeline Template:"))
        combo_layout.addWidget(self.template_combo)
        template_layout.addLayout(combo_layout)
        self.template_description_label = QLabel()
        self.template_description_label.setStyleSheet(f"color: {C.TEXT_GRAY_LIGHT}; font-style: italic;")
        template_layout.addWidget(self.template_description_label)
        self.template_combo.currentTextChanged.connect(self.on_template_change)
        left_layout.addWidget(template_card)

        # 3. Source Inputs (Stacked - one visible at a time)
        
        # 3A. Excel Input
        self.excel_card = QGroupBox("Excel Source Data")
        excel_layout = QFormLayout(self.excel_card)
        excel_input_layout = QHBoxLayout()
        self.excel_input = QLineEdit()
        self.excel_input.setPlaceholderText("Select Excel file with Reel/Shot columns...")
        browse_excel_btn = QPushButton("Browse")
        browse_excel_btn.clicked.connect(self.browse_excel_file)
        excel_input_layout.addWidget(self.excel_input)
        excel_input_layout.addWidget(browse_excel_btn)
        excel_layout.addRow("Excel File:", excel_input_layout)
        left_layout.addWidget(self.excel_card)

        # 3B. Scan Directory Input (The Auto-Scan Mode)
        self.scan_card = QGroupBox("Auto-Scan Configuration")
        scan_layout = QFormLayout(self.scan_card)
        
        # Source Folder Input
        scan_input_layout = QHBoxLayout()
        self.scan_source_input = QLineEdit()
        self.scan_source_input.setPlaceholderText("Select the Client/Incoming Drive...")
        browse_scan_btn = QPushButton("Browse")
        browse_scan_btn.clicked.connect(self.browse_scan_source)
        scan_input_layout.addWidget(self.scan_source_input)
        scan_input_layout.addWidget(browse_scan_btn)
        scan_layout.addRow("Client Drive:", scan_input_layout)
        
        # Target Reel Input (New Feature)
        self.target_reel_input = QLineEdit()
        self.target_reel_input.setPlaceholderText("e.g. REEL_01 (Leave empty to Auto-Detect)")
        scan_layout.addRow("Target Reel:", self.target_reel_input)
        
        # Options
        options_layout = QHBoxLayout()
        self.overwrite_cb = QCheckBox("Overwrite Existing")
        self.dry_run_cb = QCheckBox("Dry Run (Simulate)")
        
        # --- NEW: FAST MODE TOGGLE ---
        self.fast_mode_cb = QCheckBox("Fast Mode (Skip Checksum)")
        self.fast_mode_cb.setToolTip("Disables MD5 verification for faster transfer.")
        self.fast_mode_cb.setChecked(False)
        # -----------------------------
        
        options_layout.addWidget(self.overwrite_cb)
        options_layout.addWidget(self.dry_run_cb)
        options_layout.addWidget(self.fast_mode_cb)
        scan_layout.addRow("Options:", options_layout)
        
        # Add a note explaining what happens
        note_label = QLabel("Info: Scans Drive > Finds Shots > Builds Structure > Moves Files")
        note_label.setWordWrap(True)
        note_label.setStyleSheet(f"color: {C.ACCENT_CYAN_ALT}; font-size: {T.SIZE_XS}pt;")
        scan_layout.addRow(note_label)
        
        left_layout.addWidget(self.scan_card)

        # 4. Actions
        action_card = QGroupBox("Execution")
        action_layout = QHBoxLayout(action_card)
        
        self.create_custom_btn = QPushButton("Edit Template")
        self.create_custom_btn.clicked.connect(self.create_custom_template)
        action_layout.addWidget(self.create_custom_btn)

        self.create_btn = QPushButton("Run Process")
        self.create_btn.setObjectName("primaryButton")
        self.create_btn.clicked.connect(self.start_creation_process)
        action_layout.addWidget(self.create_btn)

        # --- PAUSE BUTTON (NEW) ---
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        action_layout.addWidget(self.pause_btn)
        # --------------------------

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_creation_process)
        self.stop_btn.setEnabled(False)
        action_layout.addWidget(self.stop_btn)

        clear_btn = QPushButton("Reset")
        clear_btn.clicked.connect(self.clear_all)
        action_layout.addWidget(clear_btn)
        left_layout.addWidget(action_card)

        # Progress
        self.progress_bar = QProgressBar()
        left_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("Ready")
        left_layout.addWidget(self.progress_label)
        self.stats_label = QLabel("Waiting for input...")
        left_layout.addWidget(self.stats_label)

        left_layout.addStretch()
        return left_widget

    # --- SMART BUTTON UPDATE ---
    def closeEvent(self, event):
        """Ensure background workers are stopped when tab closes."""
        self.stop_creation_process()
        self._cleanup_worker("excel_worker", timeout_ms=2000)
        self._cleanup_worker("folder_creation_thread", timeout_ms=2000)
        if hasattr(self, "typing_timer") and self.typing_timer.isActive():
            self.typing_timer.stop()
        super().closeEvent(event)

    def _cleanup_worker(self, attr_name: str, timeout_ms: int = 3000):
        worker = getattr(self, attr_name, None)
        if worker is None:
            return

        if worker.isRunning():
            stop = getattr(worker, "stop", None)
            if callable(stop):
                stop()
            else:
                worker.requestInterruption()
            worker.wait(timeout_ms)

        worker.deleteLater()
        if getattr(self, attr_name, None) is worker:
            setattr(self, attr_name, None)

    def _release_finished_worker(self, attr_name: str, worker) -> bool:
        if worker is not getattr(self, attr_name, None):
            return False
        setattr(self, attr_name, None)
        worker.deleteLater()
        return True

    def check_destination_status(self):
        """Dynamically check if project exists and update button text to 'Update'."""
        name = self.project_name_input.text().strip()
        root = self.project_dir_input.text().strip()
        
        if not name or not root:
            return

        # Sanitize name to match what the worker uses
        _, sanitized_name, _ = self.security_validator.sanitize_filename(name)
        
        try:
            resolved_root = get_resolved_project_root(root, sanitized_name)
            target_path = resolved_root / sanitized_name
            
            # Check if this specific project folder already exists
            if target_path.exists() and target_path.is_dir():
                # IT EXISTS -> SWITCH TO UPDATE MODE VISUALS
                if self.current_mode == "excel":
                    self.create_btn.setText("Update Project Structure")
                else:
                    self.create_btn.setText("Update & Ingest New Files")
                
                # Make it look distinct (Green for safe update)
                self.create_btn.setStyleSheet(f"background-color: {C.ACCENT_TEAL}; color: white; font-weight: {T.WEIGHT_STYLE_BOLD}; border: 1px solid #264653;")
                self.stats_label.setText("Info: Project exists. Running in SAFE UPDATE mode (No overwrites).")
                self.stats_label.setStyleSheet(f"color: {C.ACCENT_TEAL}; font-weight: {T.WEIGHT_STYLE_BOLD};")
                
            else:
                # IT DOES NOT EXIST -> SWITCH TO CREATE MODE VISUALS
                if self.current_mode == "excel":
                    self.create_btn.setText("Create Structure Only")
                else:
                    self.create_btn.setText("Build & Move Files")
                
                # Revert to default primary button style (preserve gradient effect)
                self.create_btn.setStyleSheet("background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0096C7, stop:1 #0077B6); border: 1px solid #0077B6; color: white; font-weight: bold;")
                self.stats_label.setText("Ready to create new project.")
                self.stats_label.setStyleSheet(f"color: {C.TEXT_GRAY_LIGHTER};")
                
        except (OSError, ValueError) as exc:
            logging.debug("Project path status update skipped while typing: %s", exc)

    def toggle_pause(self):
        """Toggle pause state of the worker."""
        if not hasattr(self, 'folder_creation_thread'): return
        
        if self.pause_btn.text() == "Pause":
            self.folder_creation_thread.pause()
            self.pause_btn.setText("Resume")
            self.progress_label.setText("Paused")
        else:
            self.folder_creation_thread.resume()
            self.pause_btn.setText("Pause")
            self.progress_label.setText("Resuming...")

    def set_mode(self, mode: str):
        """Called by MainWindow to switch the visible inputs."""
        self.current_mode = mode
        if mode == "excel":
            self.excel_card.setVisible(True)
            self.scan_card.setVisible(False)
            self.project_card.setTitle("Project Settings (Excel Mode)")
        else:
            self.excel_card.setVisible(False)
            self.scan_card.setVisible(True)
            self.project_card.setTitle("Project Settings (Auto-Scan Mode)")
            
        # Re-check status to update button text correctly for new mode
        self.check_destination_status()

    def create_right_panel(self):
        """Create the right panel with preview and logs."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_card = QGroupBox("Structure Preview")
        preview_layout = QVBoxLayout(preview_card)
        self.folder_preview_tree = QTreeWidget()
        self.folder_preview_tree.setHeaderLabel("Template Structure")
        preview_layout.addWidget(self.folder_preview_tree)
        right_layout.addWidget(preview_card, 1)

        log_card = QGroupBox("Process Logs")
        log_layout = QVBoxLayout(log_card)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        right_layout.addWidget(log_card, 2)

        return right_widget

    def create_custom_template(self):
        """SECURE: Create a custom template with security validation."""
        dialog = CustomTemplateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                template_data = dialog.get_template_data()
                if template_data["name"]:
                    # SECURITY: Validate template key
                    template_key = template_data["name"].lower().replace(" ", "_")
                    key_valid, sanitized_key, key_error = self.security_validator.sanitize_filename(template_key)
                    
                    if not key_valid:
                        QMessageBox.critical(self, "Security Error", 
                                           f"Invalid template key:\n{key_error}")
                        return
                    
                    # Add to config manager (this will save it)
                    self.config_manager.templates[sanitized_key] = template_data

                    # Save to file
                    success = self.config_manager.save_templates(self.config_manager.templates)
                    if success:
                        # Add to combo box and select it
                        self.template_combo.addItem(template_data["name"], sanitized_key)
                        self.template_combo.setCurrentText(template_data["name"])

                        # Notify other tabs
                        self.template_changed.emit(template_data)

                        QMessageBox.information(self, "Success", f"Custom template '{template_data['name']}' created and saved successfully!")
                    else:
                        QMessageBox.critical(self, "Error", f"Could not save custom template '{template_data['name']}'. Check logs.")
                else:
                    QMessageBox.warning(self, "Invalid Name", "Please enter a template name.")
            except SecurityError as e:
                QMessageBox.critical(self, "Security Error", f"Security violation:\n{str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Unexpected error creating template:\n{str(e)}")

    def load_templates_to_ui(self):
        """Load available templates into the combobox."""
        # Clear existing items
        self.template_combo.clear()

        # Get all available templates (defaults + user-defined)
        available_templates = self.config_manager.get_available_templates()

        # Add templates to combo box
        for key in available_templates:
            template_info = self.config_manager.templates.get(key)
            if template_info:
                display_name = template_info.get("name", key)
                self.template_combo.addItem(display_name, key)

        # Set default selection to "Standard" if it exists
        standard_index = self.template_combo.findData("standard")
        if standard_index >= 0:
            self.template_combo.setCurrentIndex(standard_index)
            # Trigger change to update preview and description
            self.on_template_change(self.template_combo.currentText())
        elif self.template_combo.count() > 0:
            # If standard doesn't exist, select the first available
            self.template_combo.setCurrentIndex(0)
            self.on_template_change(self.template_combo.currentText())

    def on_template_change(self, text):
        """Update template description and preview when selection changes."""
        current_index = self.template_combo.currentIndex()
        template_key = self.template_combo.itemData(current_index)

        if template_key:
            template_info = self.config_manager.templates.get(template_key)
            if template_info:
                description = template_info.get("description", "No description available")
                self.template_description_label.setText(description)

                # Update preview
                self.update_preview(template_key)

                # Persist template preference for cross-tab/session consistency.
                try:
                    global_settings = self.config_manager.settings.setdefault("global_settings", {})
                    global_settings["last_template_used"] = template_key
                    self.config_manager.save_settings(self.config_manager.settings)
                except Exception as e:
                    logging.debug(f"Failed to persist last template '{template_key}': {e}")

                # Notify other tabs about template change
                self.template_changed.emit(template_info)

    def update_preview(self, template_key):
        """Update the folder structure preview."""
        # Check if folder_preview_tree exists before trying to use it
        if not hasattr(self, 'folder_preview_tree') or self.folder_preview_tree is None:
            return

        # Clear existing tree
        self.folder_preview_tree.clear()

        template_info = self.config_manager.templates.get(template_key)
        if not template_info:
            return

        # Create root item
        root_item = QTreeWidgetItem(self.folder_preview_tree)
        root_item.setText(0, "Project_Root")
        root_item.setExpanded(True)

        # Add base folders
        base_folders, production_subfolders, outsource_subfolders, shot_folders = self._extract_template_lists(template_info)
        for folder in base_folders:
            base_item = QTreeWidgetItem(root_item)
            base_item.setText(0, folder)

        # Add production subfolders
        if production_subfolders:
            prod_item = QTreeWidgetItem(root_item)
            prod_item.setText(0, "04_Production")
            for folder in production_subfolders:
                sub_item = QTreeWidgetItem(prod_item)
                sub_item.setText(0, folder)

        # Add outsource subfolders
        if outsource_subfolders:
            outsource_item = QTreeWidgetItem(root_item)
            outsource_item.setText(0, "04_Production")
            for folder in outsource_subfolders:
                sub_item = QTreeWidgetItem(outsource_item)
                sub_item.setText(0, folder)

        # Add shot folders (example under a reel)
        if shot_folders:
            reels_item = QTreeWidgetItem(root_item)
            reels_item.setText(0, "05_Reels")
            shot_root = QTreeWidgetItem(reels_item)
            shot_root.setText(0, "SHOT_XXX")
            for folder in shot_folders:
                shot_item = QTreeWidgetItem(shot_root)
                shot_item.setText(0, folder)

    def browse_project_directory(self):
        """Browse for project directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Project Directory",
            self.config_manager.settings.get('last_project_directory', str(Path.home()))
        )
        if directory:
            # SECURITY: Validate directory path
            dir_path = Path(directory)
            dir_valid, dir_error = self.security_validator.validate_directory_path(dir_path, must_exist=True)
            
            if not dir_valid:
                QMessageBox.critical(self, "Security Error", f"Invalid directory:\n{dir_error}")
                return
                
            self.project_dir_input.setText(directory)
            self.config_manager.settings['last_project_directory'] = directory
            self.config_manager.save_settings(self.config_manager.settings)

    def browse_excel_file(self):
        """SECURE: Browse for Excel file with security validation."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            self.config_manager.settings.get('last_excel_file', str(Path.home())),
            "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            # SECURITY: Validate Excel file
            excel_file = Path(file_path)
            excel_valid, excel_error = SecurityValidator.validate_excel_file(excel_file)
            
            if not excel_valid:
                QMessageBox.critical(self, "Security Error", f"Invalid Excel file:\n{excel_error}")
                return
                
            self.excel_input.setText(file_path)
            self.config_manager.settings['last_excel_file'] = file_path
            self.config_manager.save_settings(self.config_manager.settings)

    def browse_scan_source(self):
        """SECURE: Browse for Client Scan directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Client/Scan Source Directory",
            self.config_manager.settings.get('last_scan_source_directory', str(Path.home()))
        )
        if directory:
            dir_path = Path(directory)
            dir_valid, dir_error = self.security_validator.validate_directory_path(dir_path, must_exist=True)
            
            if not dir_valid:
                QMessageBox.critical(self, "Security Error", f"Invalid directory:\n{dir_error}")
                return
            
            self.scan_source_input.setText(directory)
            self.config_manager.settings['last_scan_source_directory'] = directory
            self.config_manager.save_settings(self.config_manager.settings)

    def log_message(self, message: str):
        """Log a message to the log area with timestamp."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        logging.info(message)

    def update_folder_creator_progress(self, value: int, text: str):
        """Update the folder creator progress bar and label."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)
        if hasattr(self.parent(), 'statusBar'):
            self.parent().statusBar().showMessage(text, 2000)

    def _on_folder_worker_progress(self, value: int, text: str):
        if self.sender() is not self.folder_creation_thread:
            return
        self.update_folder_creator_progress(value, text)

    def _on_folder_worker_finished(self, success: bool, total_projects: int,
                                   reels_created: int, shots_created: int,
                                   folders_created: int, message: str):
        worker = self.sender()
        if not self._release_finished_worker("folder_creation_thread", worker):
            return
        self.on_folder_creation_finished(
            success, total_projects, reels_created, shots_created, folders_created, message
        )

    def on_folder_creation_finished(self, success: bool, total_projects: int,
                                   reels_created: int, shots_created: int,
                                   folders_created: int, message: str):
        """Handle folder creation completion."""
        self.is_processing = False
        self.create_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False) # Disable pause
        self.pause_btn.setText("Pause") # Reset text

        if success:
            self.log_message(f"OK: Process completed: {folders_created} folders created")
            self.stats_label.setText(f"Reels: {reels_created} | Shots: {shots_created} | Folders: {folders_created}")
            QMessageBox.information(self, "Success", f"Operation completed successfully!\n\nReels: {reels_created}\nShots: {shots_created}\nFolders: {folders_created}")
        else:
            self.log_message(f"ERROR: Process failed: {message}")
            QMessageBox.critical(self, "Error", f"Operation failed:\n{message}")

        self.progress_bar.setValue(100)
        self.progress_label.setText("Ready")

    def on_excel_loaded(self, df, error):
        """Handle the result of the async Excel load."""
        if error:
            self.is_processing = False
            self.create_btn.setEnabled(True)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Error loading Excel")
            QMessageBox.critical(self, "Excel Load Error", f"Failed to load Excel file:\n{error}")
            return

        # Success - proceed to phase 2
        self.finalize_creation_process(df=df)

    def _on_excel_worker_finished(self, df, error):
        worker = self.sender()
        if not self._release_finished_worker("excel_worker", worker):
            return
        self.on_excel_loaded(df, error)

    def finalize_creation_process(self, df=None, source_path=None):
        """Phase 2: Start the actual FolderCreationWorker."""
        
        # --- RE-GATHER SETTINGS (Guaranteed to be valid as UI was locked) ---
        project_name = self.project_name_input.text().strip()
        _, sanitized_name, _ = self.security_validator.sanitize_filename(project_name)
        
        project_dir_str = self.project_dir_input.text().strip()
        Path(project_dir_str)
        
        # --- SMART PATH FIX ---
        final_target_dir = get_resolved_project_root(project_dir_str, sanitized_name)
        if str(final_target_dir) != project_dir_str:
            self.log_message(f"Info: Smart Fix: Detected project folder selected directly. Adjusted root to: {final_target_dir}")

        # --- TEMPLATE DATA ---
        template_key = self.template_combo.currentData()
        template_info = self.config_manager.templates.get(template_key)
        base_folders, production_subfolders, outsource_subfolders, shot_folders = self._extract_template_lists(template_info)
        if not shot_folders:
            # Guardrail: avoid creating empty shot trees when template schema is mismatched.
            logging.warning(
                "Template '%s' has no shot_folders in resolved schema; using minimal defaults.",
                template_key
            )
            shot_folders = ["01_Scan", "07_Comp", "08_Output"]

        template_data = (
            base_folders,
            production_subfolders,
            outsource_subfolders,
            shot_folders,
        )
        
        target_reel = self.target_reel_input.text().strip()
        fast_mode = self.fast_mode_cb.isChecked()

        # Update UI for Phase 2
        self.create_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.log_text.clear()
        
        self.log_message(f"Starting Structure Creation in {self.current_mode.upper()} mode")
        self.log_message(f"Target: {final_target_dir / sanitized_name}")

        # --- START WORKER ---
        self._cleanup_worker("folder_creation_thread")
        self.folder_creation_thread = FolderCreationWorker(
            target_dir=final_target_dir,
            excel_df=df,
            source_scan_path=source_path,
            project_name=sanitized_name,
            template_data=template_data,
            mode="full",
            template_type=template_key,
            target_reel_name=target_reel,
            overwrite=self.overwrite_cb.isChecked(),
            dry_run=self.dry_run_cb.isChecked(),
            format_mapping=self.config_manager.format_mapping,
            fast_mode=fast_mode
        )

        self.folder_creation_thread.log_signal.connect(self.log_message)
        self.folder_creation_thread.progress_signal.connect(self._on_folder_worker_progress)
        self.folder_creation_thread.finished_signal.connect(self._on_folder_worker_finished)
        self.folder_creation_thread.start()

    def start_creation_process(self):
        """SECURE: Start the folder creation process with security validation."""
        
        if hasattr(self, 'folder_creation_thread') and self.folder_creation_thread is not None:
            if self.folder_creation_thread.isRunning():
                QMessageBox.warning(self, "Please Wait", "The previous process is still stopping.\nPlease wait a few seconds and try again.")
                return

        if self.is_processing:
            QMessageBox.warning(self, "Already Processing", "A process is already running.")
            return

        # SECURITY: Validate project name
        project_name = self.project_name_input.text().strip()
        name_valid, sanitized_name, name_error = self.security_validator.sanitize_filename(project_name)
        if not name_valid:
            QMessageBox.critical(self, "Security Error", f"Invalid project name:\n{name_error}")
            return
        self.project_name_input.setText(sanitized_name)

        # SECURITY: Validate project directory
        project_dir_str = self.project_dir_input.text().strip()
        if not project_dir_str:
            QMessageBox.critical(self, "Validation Error", "Please select a target directory.")
            return

        target_path_obj = Path(project_dir_str)
        dir_valid, dir_error = self.security_validator.validate_directory_path(target_path_obj, must_exist=True)
        if not dir_valid:
            QMessageBox.critical(self, "Security Error", f"Invalid project directory:\n{dir_error}")
            return
            
        # Validate Template
        template_key = self.template_combo.currentData()
        if not template_key:
            QMessageBox.critical(self, "Template Error", "No template selected.")
            return

        # --- MODE SPECIFIC START ---
        self.is_processing = True
        self.create_btn.setEnabled(False) # Lock UI immediately

        if self.current_mode == "excel":
            excel_path = self.excel_input.text().strip()
            if not excel_path:
                self.is_processing = False
                self.create_btn.setEnabled(True)
                QMessageBox.warning(self, "Missing Input", "Please select an Excel file.")
                return
            
            # Security Check for Excel
            try:
                excel_valid, excel_error = SecurityValidator.validate_excel_file(Path(excel_path))
                if not excel_valid:
                    self.is_processing = False
                    self.create_btn.setEnabled(True)
                    QMessageBox.critical(self, "Security Error", f"Invalid Excel: {excel_error}")
                    return
                
                # ASYNC LOAD
                self.progress_label.setText("Reading Excel File...")
                self.progress_bar.setValue(10) # Indeterminate-ish
                
                self._cleanup_worker("excel_worker")
                self.excel_worker = ExcelLoadWorker(excel_path)
                self.excel_worker.finished_signal.connect(self._on_excel_worker_finished)
                self.excel_worker.start()
                return # Exit this method, wait for signal

            except Exception as e:
                self.is_processing = False
                self.create_btn.setEnabled(True)
                QMessageBox.critical(self, "Excel Error", str(e))
                return

        else:
            # SCAN MODE
            scan_source = self.scan_source_input.text().strip()
            if not scan_source:
                self.is_processing = False
                self.create_btn.setEnabled(True)
                QMessageBox.warning(self, "Missing Input", "Please select the Client Source folder.")
                return
                
            source_path = Path(scan_source)
            if not source_path.exists():
                self.is_processing = False
                self.create_btn.setEnabled(True)
                QMessageBox.critical(self, "Error", "Source folder does not exist.")
                return
            
            # Direct start for scan mode
            self.finalize_creation_process(df=None, source_path=source_path)

    def stop_creation_process(self):
        """Stop the folder creation process."""
        if self.is_processing and self.folder_creation_thread is not None:
            self.folder_creation_thread.stop()
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage("Stopping process...", 3000)
            self.log_message("Sending stop signal to worker...")
            self.stop_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)

    def clear_all(self):
        """Clear all inputs on the Folder Creator tab."""
        self.project_name_input.clear()
        self.excel_input.clear()
        self.scan_source_input.clear()
        self.target_reel_input.clear()
        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText("Ready to start")
        self.stats_label.setText("-")

    def restore_last_paths(self):
        """SECURE: Restore last used paths from settings with validation."""
        if self.config_manager.settings.get('global_settings', {}).get("restore_last_paths", True):
            try:
                # Restore project directory
                project_dir = self.config_manager.settings.get('last_project_directory', '')
                if project_dir and Path(project_dir).exists():
                    self.project_dir_input.setText(project_dir)

                # Restore Excel file
                excel_file = self.config_manager.settings.get('last_excel_file', '')
                if excel_file and Path(excel_file).exists():
                    self.excel_input.setText(excel_file)
                    
                # Restore Scan Source
                scan_source = self.config_manager.settings.get('last_scan_source_directory', '')
                if scan_source and Path(scan_source).exists():
                    self.scan_source_input.setText(scan_source)

                # Restore template selection
                last_template = self.config_manager.settings.get('global_settings', {}).get('last_template_used', 'standard')
                if last_template in self.config_manager.get_available_templates():
                    index = self.template_combo.findData(last_template)
                    if index >= 0:
                        self.template_combo.setCurrentIndex(index)

                logging.info("Restored last used paths")
            except Exception as e:
                logging.warning(f"Could not restore last paths: {e}")

    # --- DEBOUNCE HELPERS ---
    def start_typing_timer(self):
        """Restart the typing timer for debounced validation."""
        if hasattr(self, 'typing_timer'):
            self.typing_timer.start()

    def check_destination_status(self):
        """Check if destination is valid/accessible."""
        path = self.project_dir_input.text()
        project_name = self.project_name_input.text()
        
        # Ensure we have the status label available
        if not hasattr(self, 'lbl_status_check'):
            return

        if not path or not project_name:
            self.lbl_status_check.setText("")
            return

        try:
            full_path = Path(path) / project_name
            if full_path.exists():
                self.lbl_status_check.setText("Project Exists")
                self.lbl_status_check.setStyleSheet("color: orange")
            else:
                self.lbl_status_check.setText("New Project")
                self.lbl_status_check.setStyleSheet("color: green")
        except Exception as exc:
            logging.debug("Create-folder status refresh failed: %s", exc)
