from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QRadioButton, QButtonGroup, QWidget)

class SyncDialog(QDialog):
    def __init__(self, conflicts, parent=None):
        super().__init__(parent)
        self.conflicts = conflicts
        self.resolutions = {} # shot_id -> 'local' or 'cloud'
        self.setWindowTitle("Sync Conflicts Detected")
        self.resize(800, 500)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"Found {len(self.conflicts)} conflicts between local and cloud versions."))
        layout.addWidget(QLabel("Please choose which version to keep for each shot:"))
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Shot", "Local Version", "Cloud Version", "Resolution"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        
        self.populate_table()
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        keep_local_all = QPushButton("Keep All Local")
        keep_local_all.clicked.connect(self.set_all_local)
        btn_layout.addWidget(keep_local_all)
        
        keep_cloud_all = QPushButton("Keep All Cloud")
        keep_cloud_all.clicked.connect(self.set_all_cloud)
        btn_layout.addWidget(keep_cloud_all)
        
        btn_layout.addStretch()
        
        apply_btn = QPushButton("Apply Resolution")
        apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(apply_btn)
        
        cancel_btn = QPushButton("Cancel Sync")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def populate_table(self):
        self.table.setRowCount(len(self.conflicts))
        self.groups = [] # Keep references to button groups
        
        for i, conflict in enumerate(self.conflicts):
            local = conflict['local']
            cloud = conflict['cloud']
            
            local_reel = getattr(local, "reel_episode", "")
            local_shot = getattr(local, "shot_name", "")
            self.table.setItem(i, 0, QTableWidgetItem(f"{local_reel} / {local_shot}"))
            
            # Show key differences
            local_status = getattr(local, "status", "")
            cloud_status = getattr(cloud, "status", "")
            local_description = str(getattr(local, "description", "") or "")
            cloud_description = str(getattr(cloud, "description", "") or "")
            local_desc = f"Status: {local_status}\nDesc: {local_description[:20]}..."
            cloud_desc = f"Status: {cloud_status}\nDesc: {cloud_description[:20]}..."
            
            self.table.setItem(i, 1, QTableWidgetItem(local_desc))
            self.table.setItem(i, 2, QTableWidgetItem(cloud_desc))
            
            # Radio buttons
            widget = QWidget()
            h_layout = QHBoxLayout(widget)
            h_layout.setContentsMargins(0, 0, 0, 0)
            
            rb_local = QRadioButton("Local")
            rb_cloud = QRadioButton("Cloud")
            rb_local.setChecked(True) # Default
            
            bg = QButtonGroup(widget)
            bg.addButton(rb_local, 1)
            bg.addButton(rb_cloud, 2)
            self.groups.append(bg)
            
            h_layout.addWidget(rb_local)
            h_layout.addWidget(rb_cloud)
            
            self.table.setCellWidget(i, 3, widget)
            
            # Default resolution
            self.resolutions[conflict['shot_id']] = 'local'
            
            # Connect
            bg.buttonClicked.connect(lambda btn, idx=i, sid=conflict['shot_id']: self.update_resolution(idx, sid))

    def update_resolution(self, row_idx, shot_id):
        bg = self.groups[row_idx]
        if bg.checkedId() == 1:
            self.resolutions[shot_id] = 'local'
        else:
            self.resolutions[shot_id] = 'cloud'
            
    def set_all_local(self):
        for bg in self.groups:
            bg.button(1).setChecked(True)
            # Trigger update? simpler to just reset resolutions dict
        for c in self.conflicts:
            self.resolutions[c['shot_id']] = 'local'
            
    def set_all_cloud(self):
        for bg in self.groups:
            bg.button(2).setChecked(True)
        for c in self.conflicts:
            self.resolutions[c['shot_id']] = 'cloud'
            
    def get_resolutions(self):
        # Ensure we capture current state
        for i, conflict in enumerate(self.conflicts):
            bg = self.groups[i]
            if bg.checkedId() == 1:
                self.resolutions[conflict['shot_id']] = 'local'
            else:
                self.resolutions[conflict['shot_id']] = 'cloud'
        return self.resolutions
