from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QDialog, QFormLayout, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import bcrypt

class AdminUsersTab(QWidget):
    def __init__(self, user_role="Admin", user_data=None, parent=None):
        super().__init__(parent)
        self.user_role = user_role
        self.user_data = user_data or {}
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        header_title = QLabel("User Management")
        header_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white;")
        main_layout.addWidget(header_title)
        
        # Access control
        if self.user_role.lower() not in ["hr", "admin", "developer"]:
            lbl = QLabel("You do not have permission to access User Management.")
            lbl.setStyleSheet("color: #ef4444; font-size: 14px;")
            main_layout.addWidget(lbl)
            main_layout.addStretch()
            return
            
        controls = QHBoxLayout()
        add_btn = QPushButton("Add New User")
        add_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        add_btn.clicked.connect(self.add_user)
        controls.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Role/Dept")
        edit_btn.setStyleSheet("background-color: #f59e0b; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        edit_btn.clicked.connect(self.edit_user)
        controls.addWidget(edit_btn)
        
        reset_btn = QPushButton("Reset Password")
        reset_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        reset_btn.clicked.connect(self.reset_password)
        controls.addWidget(reset_btn)
        
        controls.addStretch()
        main_layout.addLayout(controls)

        self.grid = QTableWidget(0, 4)
        self.grid.setHorizontalHeaderLabels(["Username", "Display Name", "Department (Job Title)", "Roles"])
        self.style_table(self.grid)
        self.load_data()
        
        main_layout.addWidget(self.grid)

    def load_data(self):
        try:
            from ut_vfx.core.infra.database_manager import database_manager
            query = "SELECT username, display_name, job_title, roles FROM ut_users ORDER BY username ASC"
            users = database_manager.execute_query(query) or []
        except Exception:
            users = []
            
        self.grid.setRowCount(len(users))
        for r, row in enumerate(users):
            self.grid.setItem(r, 0, QTableWidgetItem(str(row.get('username', ''))))
            self.grid.setItem(r, 1, QTableWidgetItem(str(row.get('display_name', ''))))
            self.grid.setItem(r, 2, QTableWidgetItem(str(row.get('job_title', ''))))
            self.grid.setItem(r, 3, QTableWidgetItem(str(row.get('roles', ''))))

    def add_user(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New User")
        dialog.setStyleSheet("background-color: #1e1e1e; color: white;")
        layout = QFormLayout(dialog)
        
        username_input = QLineEdit()
        display_input = QLineEdit()
        dept_input = QComboBox()
        dept_input.addItems(["General", "Compositing", "3D", "Production", "IT", "HR", "Admin"])
        dept_input.setStyleSheet("background: #2d2d2d; padding: 4px;")
        
        role_input = QComboBox()
        role_input.addItems(["Artist", "Supervisor", "HR", "Admin"])
        role_input.setStyleSheet("background: #2d2d2d; padding: 4px;")
        
        pass_input = QLineEdit()
        pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addRow("Username:", username_input)
        layout.addRow("Display Name:", display_input)
        layout.addRow("Department:", dept_input)
        layout.addRow("Role:", role_input)
        layout.addRow("Password:", pass_input)
        
        btn_box = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color: #10b981; font-weight: bold; padding: 4px;")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addRow(btn_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            u = username_input.text().strip().lower()
            d = display_input.text().strip()
            jt = dept_input.currentText()
            r = role_input.currentText()
            p = pass_input.text()
            
            if not u or not p:
                QMessageBox.warning(self, "Error", "Username and Password are required.")
                return
                
            hashed = bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            try:
                from ut_vfx.core.infra.database_manager import database_manager
                query = "INSERT INTO ut_users (username, password_hash, display_name, job_title, roles) VALUES (%s, %s, %s, %s, %s)"
                database_manager.execute_query(query, (u, hashed, d, jt, r), fetch=False)
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add user: {e}")

    def edit_user(self):
        selected_rows = set(item.row() for item in self.grid.selectedItems())
        if not selected_rows:
            QMessageBox.warning(self, "Selection Error", "Please select a user to edit.")
            return
            
        row = list(selected_rows)[0]
        item0 = self.grid.item(row, 0)
        item2 = self.grid.item(row, 2)
        item3 = self.grid.item(row, 3)
        username = item0.text() if item0 else ""
        current_dept = item2.text() if item2 else ""
        current_role = item3.text() if item3 else ""
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit {username}")
        dialog.setStyleSheet("background-color: #1e1e1e; color: white;")
        layout = QFormLayout(dialog)
        
        dept_input = QComboBox()
        dept_input.addItems(["General", "Compositing", "3D", "Production", "IT", "HR", "Admin"])
        dept_input.setCurrentText(current_dept)
        dept_input.setStyleSheet("background: #2d2d2d; padding: 4px;")
        
        role_input = QComboBox()
        role_input.addItems(["Artist", "Supervisor", "HR", "Admin"])
        role_input.setCurrentText(current_role)
        role_input.setStyleSheet("background: #2d2d2d; padding: 4px;")
        
        layout.addRow("Department:", dept_input)
        layout.addRow("Role:", role_input)
        
        btn_box = QHBoxLayout()
        save_btn = QPushButton("Update")
        save_btn.setStyleSheet("background-color: #10b981; font-weight: bold; padding: 4px;")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addRow(btn_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            jt = dept_input.currentText()
            r = role_input.currentText()
            try:
                from ut_vfx.core.infra.database_manager import database_manager
                database_manager.execute_query("UPDATE ut_users SET job_title=%s, roles=%s WHERE username=%s", (jt, r, username), fetch=False)
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to update user: {e}")

    def reset_password(self):
        selected_rows = set(item.row() for item in self.grid.selectedItems())
        if not selected_rows:
            QMessageBox.warning(self, "Selection Error", "Please select a user to reset password.")
            return
            
        row = list(selected_rows)[0]
        item0 = self.grid.item(row, 0)
        username = item0.text() if item0 else ""
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Reset Password for {username}")
        dialog.setStyleSheet("background-color: #1e1e1e; color: white;")
        layout = QFormLayout(dialog)
        
        pass_input = QLineEdit()
        pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("New Password:", pass_input)
        
        btn_box = QHBoxLayout()
        save_btn = QPushButton("Reset")
        save_btn.setStyleSheet("background-color: #ef4444; font-weight: bold; padding: 4px;")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addRow(btn_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            p = pass_input.text()
            if not p:
                QMessageBox.warning(self, "Error", "Password cannot be empty.")
                return
            hashed = bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            try:
                from ut_vfx.core.infra.database_manager import database_manager
                database_manager.execute_query("UPDATE ut_users SET password_hash=%s WHERE username=%s", (hashed, username), fetch=False)
                QMessageBox.information(self, "Success", f"Password reset for {username}.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to reset password: {e}")

    def style_table(self, table: QTableWidget):
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setStyleSheet("""
            QTableWidget { background-color: #1e1e1e; color: #e0e0e0; gridline-color: #333333; border: 1px solid #333; font-size: 12px; }
            QTableWidget::item:alternate { background-color: #252525; }
            QTableWidget::item:selected { background-color: #005a9e; color: white; }
            QHeaderView::section { background-color: #2d2d2d; color: #aaa; border: 1px solid #333; padding: 4px; font-weight: bold; }
        """)
