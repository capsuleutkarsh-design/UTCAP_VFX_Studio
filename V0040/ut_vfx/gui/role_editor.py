from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QCheckBox, QPushButton, QLabel, QMessageBox,
    QInputDialog, QGridLayout, QFrame
)
from PySide6.QtCore import Qt

from ut_vfx.core.domain.user_manager import UserManager

class RoleEditor(QWidget):
    """
    Admin UI for editing Dynamic Roles.
    Allows creating roles and assigning permissions (Enabled Tabs).
    """
    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.current_role = None
        
        # Available Permissions (Mapped to Tab Names for now)
        self.available_permissions = [
            "Folder Creator", "Move/Scan", "Reports", 
            "Stock Browser", "Rename Tool", "Dashboard", 
            "Tester Panel", "Settings", "Admin Panel",
            "Attendance", "Shot Review"
        ]
        
        self.setup_ui()
        self.refresh_roles()

    def setup_ui(self):
        # Main Layout (No Margins to fit nicely in parent tab)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # CARD CONTAINER
        # Wraps everything in a distinct background to avoid the "void" look
        self.card = QFrame()
        self.card.setObjectName("RoleEditorCard")
        self.card.setStyleSheet("""
            QFrame#RoleEditorCard {
                background-color: #1E1E1E;
                border-radius: 12px;
                border: 1px solid #333;
            }
            QLabel {
                border: none;
                color: #DDD;
            }
            QListWidget {
                background-color: #151515;
                border: 1px solid #333;
                border-radius: 6px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                color: #AAA;
            }
            QListWidget::item:selected {
                background-color: #00B4D8;
                color: black;
                border-radius: 4px;
            }
            QCheckBox {
                color: #CCC;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #555;
                background: #252525;
            }
            QCheckBox::indicator:checked {
                background: #00B4D8;
                border: 1px solid #00B4D8;
            }
        """)
        
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(20)

        # --- LEFT PANEL: ROLE LIST ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_roles = QLabel("ROLES")
        lbl_roles.setStyleSheet("font-size: 14px; font-weight: bold; color: #888; letter-spacing: 1px;")
        left_layout.addWidget(lbl_roles)
        
        self.role_list = QListWidget()
        self.role_list.setFixedWidth(220) # Fixed width for sidebar feel
        self.role_list.itemClicked.connect(self.on_role_selected)
        left_layout.addWidget(self.role_list)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("New Role")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setStyleSheet("background-color: #252525; color: white; border: 1px solid #444; border-radius: 4px; padding: 6px;")
        self.btn_add.clicked.connect(self.add_role)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("background-color: #331111; color: #FF5555; border: 1px solid #522; border-radius: 4px; padding: 6px;")
        self.btn_delete.clicked.connect(self.delete_role)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        left_layout.addLayout(btn_layout)
        
        # --- RIGHT PANEL: PERMISSIONS GRID ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        self.lbl_editing = QLabel("Select a role to edit permissions")
        self.lbl_editing.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin-bottom: 10px;")
        right_layout.addWidget(self.lbl_editing)
        
        # Grid Container
        perm_container = QFrame()
        perm_container.setStyleSheet("background-color: #151515; border-radius: 8px; border: 1px solid #2A2A2A;")
        perm_layout = QVBoxLayout(perm_container)
        perm_layout.setContentsMargins(20, 20, 20, 20)
        
        # Instructo
        lbl_hint = QLabel("Check the tabs this role is allowed to access:")
        lbl_hint.setStyleSheet("color: #666; font-style: italic; margin-bottom: 15px;")
        perm_layout.addWidget(lbl_hint)

        # The actual Grid of Checkboxes
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(0,0,0,0)
        
        self.checkboxes = {}
        row, col = 0, 0
        for perm in self.available_permissions:
            cb = QCheckBox(perm)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.stateChanged.connect(self.on_perm_changed)
            self.checkboxes[perm] = cb
            
            # Simple 3-column grid
            self.grid_layout.addWidget(cb, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
        perm_layout.addWidget(self.grid_widget)
        perm_layout.addStretch() # Push everything up
        
        right_layout.addWidget(perm_container)
        right_layout.addStretch() # Push container up
        
        # Add panels to Card Layout
        card_layout.addWidget(left_panel)
        card_layout.addWidget(right_panel, stretch=1) # Right side expands
        
        # Add Card to Main Layout
        main_layout.addWidget(self.card)

    def refresh_roles(self):
        self.role_list.clear()
        roles = self.user_manager.get_available_roles()
        for role in roles:
            item = QListWidgetItem(role)
            self.role_list.addItem(item)
            
        # Reset Interaction State
        self.current_role = None
        self.lbl_editing.setText("Select a role to edit")
        self.block_signals_checkboxes(True)
        for cb in self.checkboxes.values():
            cb.setChecked(False)
            cb.setEnabled(False)
            cb.setStyleSheet("color: #555;") # Dim disabled
        self.block_signals_checkboxes(False)

    def on_role_selected(self, item):
        self.current_role = item.text()
        self.lbl_editing.setText(f"Permissions: <span style='color:#00B4D8;'>{self.current_role.upper()}</span>")
        
        # Load Permissions
        allowed = self.user_manager.get_allowed_tabs([self.current_role])
        special_all = "ALL" in allowed
        
        self.block_signals_checkboxes(True)
        for perm, cb in self.checkboxes.items():
            cb.setEnabled(True)
            if special_all or perm in allowed:
                cb.setChecked(True)
                cb.setStyleSheet("color: white; font-weight: bold;")
            else:
                cb.setChecked(False)
                cb.setStyleSheet("color: #AAA;")
        self.block_signals_checkboxes(False)

    def block_signals_checkboxes(self, block):
        for cb in self.checkboxes.values():
            cb.blockSignals(block)

    def on_perm_changed(self):
        if not self.current_role: return
        
        new_perms = []
        for perm, cb in self.checkboxes.items():
            if cb.isChecked():
                new_perms.append(perm)
                cb.setStyleSheet("color: white; font-weight: bold;")
            else:
                cb.setStyleSheet("color: #AAA;")
        
        # Save immediately (Auto-Save)
        self.user_manager.update_role_permissions(self.current_role, new_perms)
        
    def add_role(self):
        name, ok = QInputDialog.getText(self, "New Role", "Role Name:")
        if ok and name:
            name = name.strip()
            if name in self.user_manager.get_available_roles():
                QMessageBox.warning(self, "Error", "Role already exists!")
                return
            
            # Create with empty perms
            self.user_manager.create_role(name, [])
            self.refresh_roles()
            
    def delete_role(self):
        if not self.current_role: return
        if self.current_role.lower() == "developer":  # Case-insensitive
            QMessageBox.critical(self, "Error", "Cannot delete Developer role!")
            return

            
        confirm = QMessageBox.question(self, "Confirm", f"Delete role '{self.current_role}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.user_manager.delete_role(self.current_role)
            self.refresh_roles()
