from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QDialog, QFormLayout, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

class AddDeploymentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Software Deployment")
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        layout = QFormLayout(self)
        
        self.pkg_input = QLineEdit()
        self.target_input = QLineEdit()

        layout.addRow("Package Name:", self.pkg_input)
        layout.addRow("Target Machine:", self.target_input)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Deploy")
        save_btn.setStyleSheet("background-color: #3b82f6; font-weight: bold; padding: 5px;")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #6b7280; font-weight: bold; padding: 5px;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

class ItDeploymentTab(QWidget):
    def __init__(self, user_data=None, parent=None):
        super().__init__(parent)
        self.user_data = user_data or {}
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.build_ui(main_layout)

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"background-color: #2a2a2a; border-left: 4px solid {color}; border-radius: 4px;")
        lay = QVBoxLayout(card)
        
        t_label = QLabel(title)
        t_label.setFont(QFont("Inter", 10))
        t_label.setStyleSheet("color: #aaa;")
        
        v_label = QLabel(str(value))
        v_label.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        v_label.setStyleSheet("color: white;")
        
        lay.addWidget(t_label)
        lay.addWidget(v_label)
        return card, v_label

    def build_ui(self, main_layout):
        header_title = QLabel("Software Deployment (IT)")
        header_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white;")
        main_layout.addWidget(header_title)
        
        # Summary Cards
        cards_lay = QHBoxLayout()
        card1, self.lbl_total = self.create_stat_card("Total Deployments", "0", "#3b82f6")
        card2, self.lbl_success = self.create_stat_card("Success Rate", "0%", "#10b981")
        card3, self.lbl_pending = self.create_stat_card("Pending Deployments", "0", "#f59e0b")
        cards_lay.addWidget(card1)
        cards_lay.addWidget(card2)
        cards_lay.addWidget(card3)
        main_layout.addLayout(cards_lay)
        
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Status:"))
        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["All", "Pending", "Success", "Failed"])
        self.filter_cb.setStyleSheet("background: #2d2d2d; color: white; padding: 4px; border: 1px solid #444;")
        self.filter_cb.currentTextChanged.connect(self.load_data)
        controls.addWidget(self.filter_cb)
        
        add_btn = QPushButton("Deploy New Package")
        add_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        add_btn.clicked.connect(self.add_deployment)
        controls.addWidget(add_btn)
        
        success_btn = QPushButton("Mark Success")
        success_btn.setStyleSheet("background-color: #10b981; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        success_btn.clicked.connect(lambda: self.update_status("Success"))
        controls.addWidget(success_btn)
        
        fail_btn = QPushButton("Mark Failed")
        fail_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        fail_btn.clicked.connect(lambda: self.update_status("Failed"))
        controls.addWidget(fail_btn)
        
        controls.addStretch()
        main_layout.addLayout(controls)

        self.grid = QTableWidget(0, 6)
        self.grid.setHorizontalHeaderLabels(["ID", "Package Name", "Target Machine", "Deployed By", "Status", "Deployed At"])
        self.style_table(self.grid)
        self.load_data()
        
        self.grid.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.grid.hideColumn(0) # Hide ID
        main_layout.addWidget(self.grid)

    def load_data(self):
        try:
            from ut_vfx.core.infra.database_manager import database_manager
            status_filter = self.filter_cb.currentText()
            where_clause = ""
            if status_filter != "All":
                where_clause = f"WHERE status = '{status_filter}'"
                
            query = f"SELECT * FROM it_deployments {where_clause} ORDER BY id DESC"
            deps = database_manager.execute_query(query) or []
            
            # Update stats based on all deployments regardless of filter
            all_deps = database_manager.execute_query("SELECT status FROM it_deployments") or []
        except:
            deps = []
            all_deps = []
            
        self.grid.setRowCount(len(deps))
        
        total = len(all_deps)
        successes = sum(1 for d in all_deps if d.get('status') == 'Success')
        pending = sum(1 for d in all_deps if d.get('status') == 'Pending')
        
        self.lbl_total.setText(str(total))
        self.lbl_pending.setText(str(pending))
        if total > 0:
            self.lbl_success.setText(f"{int((successes/total)*100)}%")
        else:
            self.lbl_success.setText("0%")

        for r, row in enumerate(deps):
            self.grid.setItem(r, 0, QTableWidgetItem(str(row.get('id', ''))))
            self.grid.setItem(r, 1, QTableWidgetItem(str(row.get('package_name', ''))))
            self.grid.setItem(r, 2, QTableWidgetItem(str(row.get('target_machine', ''))))
            self.grid.setItem(r, 3, QTableWidgetItem(str(row.get('deployed_by', ''))))
            
            status_item = QTableWidgetItem(str(row.get('status', '')))
            if status_item.text() == "Success":
                status_item.setForeground(QColor("green"))
            elif status_item.text() == "Failed":
                status_item.setForeground(QColor("red"))
            elif status_item.text() == "Pending":
                status_item.setForeground(QColor("yellow"))
            self.grid.setItem(r, 4, status_item)
            
            self.grid.setItem(r, 5, QTableWidgetItem(str(row.get('deployed_at', ''))))

    def add_deployment(self):
        dialog = AddDeploymentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            pkg = dialog.pkg_input.text().replace("'", "''")
            tgt = dialog.target_input.text().replace("'", "''")
            
            if not pkg or not tgt:
                QMessageBox.warning(self, "Error", "Package Name and Target Machine are required.")
                return
                
            from ut_vfx.core.infra.database_manager import database_manager
            current_user = self.user_data.get('username', 'admin')
            query = f"INSERT INTO it_deployments (package_name, target_machine, deployed_by, status) VALUES ('{pkg}', '{tgt}', '{current_user}', 'Pending')"
            if database_manager.execute_query(query, fetch=False):
                QMessageBox.information(self, "Success", "Deployment task created.")
                self.load_data()

    def update_status(self, new_status):
        selected_rows = set(item.row() for item in self.grid.selectedItems())
        if not selected_rows:
            QMessageBox.warning(self, "Selection Empty", "Please select a deployment to update.")
            return
            
        from ut_vfx.core.infra.database_manager import database_manager
        for r in selected_rows:
            did = self.grid.item(r, 0).text()
            query = f"UPDATE it_deployments SET status = '{new_status}' WHERE id = {did}"
            database_manager.execute_query(query, fetch=False)
        self.load_data()
            
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
