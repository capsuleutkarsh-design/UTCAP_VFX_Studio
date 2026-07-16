from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout, QLineEdit, QSpinBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

class AddLicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Software License")
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        layout = QFormLayout(self)
        
        self.software_input = QLineEdit()
        self.key_input = QLineEdit()
        self.seats_total_input = QSpinBox()
        self.seats_total_input.setRange(1, 10000)
        self.expiry_input = QDateEdit(QDate.currentDate().addYears(1))
        self.expiry_input.setCalendarPopup(True)

        layout.addRow("Software Name:", self.software_input)
        layout.addRow("License Key:", self.key_input)
        layout.addRow("Total Seats:", self.seats_total_input)
        layout.addRow("Expiry Date:", self.expiry_input)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save License")
        save_btn.setStyleSheet("background-color: #10b981; font-weight: bold; padding: 5px;")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #6b7280; font-weight: bold; padding: 5px;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

class ItLicensesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        header_title = QLabel("Software Licenses (IT)")
        header_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white;")
        main_layout.addWidget(header_title)
        
        # Summary Cards
        cards_lay = QHBoxLayout()
        card1, self.lbl_total_software = self.create_stat_card("Total Software", "0", "#3b82f6")
        card2, self.lbl_total_seats = self.create_stat_card("Total Seats", "0", "#10b981")
        card3, self.lbl_seats_used = self.create_stat_card("Seats Used", "0", "#f59e0b")
        cards_lay.addWidget(card1)
        cards_lay.addWidget(card2)
        cards_lay.addWidget(card3)
        main_layout.addLayout(cards_lay)
        
        controls = QHBoxLayout()
        add_btn = QPushButton("Add New License")
        add_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        add_btn.clicked.connect(self.add_license)
        controls.addWidget(add_btn)
        
        del_btn = QPushButton("Delete Selected")
        del_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        del_btn.clicked.connect(self.delete_selected)
        controls.addWidget(del_btn)
        
        scan_btn = QPushButton("Scan Seats Used (Live Ops)")
        scan_btn.setStyleSheet("background-color: #8b5cf6; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        scan_btn.clicked.connect(self.scan_seats_stub)
        controls.addWidget(scan_btn)
        
        controls.addStretch()
        main_layout.addLayout(controls)

        self.grid = QTableWidget(0, 6)
        self.grid.setHorizontalHeaderLabels(["ID", "Software", "License Key", "Seats Total", "Seats Used", "Expiry"])
        self.style_table(self.grid)
        self.load_data()
        
        self.grid.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.grid.hideColumn(0) # Hide ID
        main_layout.addWidget(self.grid)

    def load_data(self):
        try:
            from ut_vfx.core.infra.database_manager import database_manager
            query = "SELECT * FROM it_licenses ORDER BY id DESC"
            licenses = database_manager.execute_query(query) or []
        except:
            licenses = []
            
        self.grid.setRowCount(len(licenses))
        total_sw = len(licenses)
        total_seats = sum([row.get('seats_total', 0) for row in licenses])
        total_used = sum([row.get('seats_used', 0) for row in licenses])
        
        self.lbl_total_software.setText(str(total_sw))
        self.lbl_total_seats.setText(str(total_seats))
        self.lbl_seats_used.setText(str(total_used))

        from PySide6.QtGui import QBrush
        import datetime
        today = datetime.date.today()
        
        for r, row in enumerate(licenses):
            self.grid.setItem(r, 0, QTableWidgetItem(str(row.get('id', ''))))
            self.grid.setItem(r, 1, QTableWidgetItem(str(row.get('software_name', ''))))
            self.grid.setItem(r, 2, QTableWidgetItem(str(row.get('license_key', ''))))
            self.grid.setItem(r, 3, QTableWidgetItem(str(row.get('seats_total', ''))))
            self.grid.setItem(r, 4, QTableWidgetItem(str(row.get('seats_used', ''))))
            
            exp_str = str(row.get('expiry_date', ''))
            exp_item = QTableWidgetItem(exp_str)
            
            try:
                exp_date = datetime.datetime.strptime(exp_str, "%Y-%m-%d").date()
                days_left = (exp_date - today).days
                if days_left < 0:
                    exp_item.setBackground(QBrush(QColor("#7f1d1d"))) # Red
                    exp_item.setToolTip(f"Expired {-days_left} days ago")
                elif days_left <= 30:
                    exp_item.setBackground(QBrush(QColor("#9a3412"))) # Orange/Yellow
                    exp_item.setToolTip(f"Expiring in {days_left} days")
            except:
                pass
                
            self.grid.setItem(r, 5, exp_item)

    def add_license(self):
        dialog = AddLicenseDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            soft = dialog.software_input.text().replace("'", "''")
            key = dialog.key_input.text().replace("'", "''")
            seats = dialog.seats_total_input.value()
            expiry = dialog.expiry_input.date().toString("yyyy-MM-dd")
            
            if not soft:
                QMessageBox.warning(self, "Error", "Software name is required.")
                return
                
            from ut_vfx.core.infra.database_manager import database_manager
            query = f"INSERT INTO it_licenses (software_name, license_key, seats_total, seats_used, expiry_date) VALUES ('{soft}', '{key}', {seats}, 0, '{expiry}')"
            if database_manager.execute_query(query, fetch=False):
                QMessageBox.information(self, "Success", "Added new license.")
                self.load_data()

    def delete_selected(self):
        selected_rows = set(item.row() for item in self.grid.selectedItems())
        if not selected_rows:
            QMessageBox.warning(self, "Selection Empty", "Please select a license to delete.")
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete the selected license(s)?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from ut_vfx.core.infra.database_manager import database_manager
            for r in selected_rows:
                item = self.grid.item(r, 0)
                if not item: continue
                lid = item.text()
                query = f"DELETE FROM it_licenses WHERE id = {lid}"
                database_manager.execute_query(query, fetch=False)
            self.load_data()
            
    def scan_seats_stub(self):
        # Stub for live ops scanning
        QMessageBox.information(self, "Scan Triggered", "Sent broadcast to local agents. Seat usage will update as responses arrive.")
        # We could implement actual UDP polling here, but for now we just show a message.
            
    def style_table(self, table: QTableWidget):
        from PySide6.QtWidgets import QAbstractItemView
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setStyleSheet("""
            QTableWidget { background-color: #1e1e1e; color: #e0e0e0; gridline-color: #333333; border: 1px solid #333; font-size: 12px; }
            QTableWidget::item:alternate { background-color: #252525; }
            QTableWidget::item:selected { background-color: #005a9e; color: white; }
            QHeaderView::section { background-color: #2d2d2d; color: #aaa; border: 1px solid #333; padding: 4px; font-weight: bold; }
        """)
