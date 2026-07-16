from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout, QLineEdit, QDateEdit, QComboBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

class AddMilestoneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Milestone")
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        layout = QFormLayout(self)
        
        self.proj_cb = QComboBox()
        self.proj_cb.setStyleSheet("background: #2d2d2d; color: white; padding: 4px;")
        
        # Populate project code dropdown
        from ut_vfx.core.infra.database_manager import database_manager
        projects = database_manager.execute_query("SELECT DISTINCT project_code FROM tracking_projects") or []
        for p in projects:
            self.proj_cb.addItem(p.get("project_code"))
            
        if not projects:
            self.proj_cb.addItem("N/A")
            
        self.dep_cb = QComboBox()
        self.dep_cb.setStyleSheet("background: #2d2d2d; color: white; padding: 4px;")
        
        self.proj_cb.currentTextChanged.connect(self.update_deps)
            
        self.ms_input = QLineEdit()
        self.start_input = QDateEdit(QDate.currentDate())
        self.start_input.setCalendarPopup(True)
        self.end_input = QDateEdit(QDate.currentDate().addDays(14))
        self.end_input.setCalendarPopup(True)

        layout.addRow("Project Code:", self.proj_cb)
        layout.addRow("Milestone Name:", self.ms_input)
        layout.addRow("Depends On:", self.dep_cb)
        layout.addRow("Start Date:", self.start_input)
        layout.addRow("End Date:", self.end_input)
        
        self.update_deps()
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color: #3b82f6; font-weight: bold; padding: 5px;")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #6b7280; font-weight: bold; padding: 5px;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
    def update_deps(self):
        self.dep_cb.clear()
        self.dep_cb.addItem("None", None)
        proj = self.proj_cb.currentText()
        if proj and proj != "N/A":
            from ut_vfx.core.infra.database_manager import database_manager
            ms_list = database_manager.execute_query(f"SELECT id, milestone FROM prod_scheduling WHERE project_code = '{proj}' ORDER BY start_date ASC") or []
            for ms in ms_list:
                self.dep_cb.addItem(ms.get('milestone'), ms.get('id'))

class ShiftDatesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shift Dates")
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Shift by (days):"))
        from PySide6.QtWidgets import QSpinBox
        self.days_spin = QSpinBox()
        self.days_spin.setRange(-1000, 1000)
        self.days_spin.setValue(1)
        self.days_spin.setStyleSheet("padding: 4px;")
        layout.addWidget(self.days_spin)
        
        btn_box = QHBoxLayout()
        ok_btn = QPushButton("Shift Downstream")
        ok_btn.setStyleSheet("background-color: #f59e0b; color: white; font-weight: bold;")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(ok_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

class ProdSchedulingTab(QWidget):
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
        header_title = QLabel("Production Scheduling")
        header_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white;")
        main_layout.addWidget(header_title)
        
        # Summary Cards
        cards_lay = QHBoxLayout()
        card1, self.lbl_active = self.create_stat_card("Active Projects", "0", "#3b82f6")
        card2, self.lbl_upcoming = self.create_stat_card("Upcoming Milestones", "0", "#f59e0b")
        card3, self.lbl_completed = self.create_stat_card("Completed Milestones", "0", "#10b981")
        cards_lay.addWidget(card1)
        cards_lay.addWidget(card2)
        cards_lay.addWidget(card3)
        main_layout.addLayout(cards_lay)
        
        controls = QHBoxLayout()
        add_btn = QPushButton("Add New Milestone")
        add_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        add_btn.clicked.connect(self.add_milestone)
        controls.addWidget(add_btn)
        
        update_btn = QPushButton("Update Status")
        update_btn.setStyleSheet("background-color: #10b981; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        update_btn.clicked.connect(self.update_status)
        controls.addWidget(update_btn)
        
        shift_btn = QPushButton("Shift Dates (Dependency)")
        shift_btn.setStyleSheet("background-color: #f59e0b; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        shift_btn.clicked.connect(self.shift_dates)
        controls.addWidget(shift_btn)
        
        controls.addStretch()
        main_layout.addLayout(controls)

        self.grid = QTableWidget(0, 7)
        self.grid.setHorizontalHeaderLabels(["ID", "Project Code", "Milestone", "Depends On", "Start Date", "End Date", "Status"])
        self.style_table(self.grid)
        self.load_data()
        
        self.grid.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.grid.hideColumn(0) # Hide ID
        main_layout.addWidget(self.grid)

    def load_data(self):
        try:
            from ut_vfx.core.infra.database_manager import database_manager
            query = "SELECT * FROM prod_scheduling ORDER BY id DESC"
            sched = database_manager.execute_query(query) or []
        except:
            sched = []
            
        self.grid.setRowCount(len(sched))
        
        projects = set(row.get('project_code') for row in sched)
        completed = sum(1 for row in sched if row.get('status') == 'Completed')
        upcoming = len(sched) - completed
        
        self.lbl_active.setText(str(len(projects)))
        self.lbl_upcoming.setText(str(upcoming))
        self.lbl_completed.setText(str(completed))

        for r, row in enumerate(sched):
            self.grid.setItem(r, 0, QTableWidgetItem(str(row.get('id', ''))))
            self.grid.setItem(r, 1, QTableWidgetItem(str(row.get('project_code', ''))))
            self.grid.setItem(r, 2, QTableWidgetItem(str(row.get('milestone', ''))))
            
            dep_id = row.get('depends_on_id')
            dep_name = "None"
            if dep_id:
                dep_row = next((x for x in sched if x.get('id') == dep_id), None)
                if dep_row: dep_name = dep_row.get('milestone', str(dep_id))
            self.grid.setItem(r, 3, QTableWidgetItem(dep_name))
            
            self.grid.setItem(r, 4, QTableWidgetItem(str(row.get('start_date', ''))))
            self.grid.setItem(r, 5, QTableWidgetItem(str(row.get('end_date', ''))))
            
            status_item = QTableWidgetItem(str(row.get('status', '')))
            if status_item.text() == "Completed":
                status_item.setForeground(QColor("green"))
            elif status_item.text() == "In Progress":
                status_item.setForeground(QColor("yellow"))
            self.grid.setItem(r, 6, status_item)

    def add_milestone(self):
        dialog = AddMilestoneDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proj = dialog.proj_cb.currentText()
            ms = dialog.ms_input.text().replace("'", "''")
            start = dialog.start_input.date().toString("yyyy-MM-dd")
            end = dialog.end_input.date().toString("yyyy-MM-dd")
            dep_id = dialog.dep_cb.currentData()
            
            if not proj or not ms or proj == "N/A":
                QMessageBox.warning(self, "Error", "Project Code and Milestone Name are required.")
                return
                
            from ut_vfx.core.infra.database_manager import database_manager
            
            dep_val = str(dep_id) if dep_id else "NULL"
            query = f"INSERT INTO prod_scheduling (project_code, milestone, start_date, end_date, status, depends_on_id) VALUES ('{proj}', '{ms}', '{start}', '{end}', 'Scheduled', {dep_val})"
            if database_manager.execute_query(query, fetch=False):
                QMessageBox.information(self, "Success", "Added new scheduling milestone.")
                self.load_data()

    def update_status(self):
        selected_rows = set(item.row() for item in self.grid.selectedItems())
        if not selected_rows:
            QMessageBox.warning(self, "Selection Empty", "Please select a milestone to update.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Update Status")
        dialog.setStyleSheet("background-color: #1e1e1e; color: white;")
        lay = QVBoxLayout(dialog)
        lay.addWidget(QLabel("Select new status:"))
        cb = QComboBox()
        cb.addItems(["Scheduled", "In Progress", "Completed"])
        cb.setStyleSheet("background: #2d2d2d; padding: 4px;")
        lay.addWidget(cb)
        
        btn_box = QHBoxLayout()
        ok_btn = QPushButton("Update")
        ok_btn.setStyleSheet("background-color: #10b981; font-weight:bold;")
        ok_btn.clicked.connect(dialog.accept)
        btn_box.addWidget(ok_btn)
        lay.addLayout(btn_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_status = cb.currentText()
            from ut_vfx.core.infra.database_manager import database_manager
            for r in selected_rows:
                item = self.grid.item(r, 0)
                if item:
                    mid = item.text()
                    query = f"UPDATE prod_scheduling SET status = '{new_status}' WHERE id = {mid}"
                    database_manager.execute_query(query, fetch=False)
            self.load_data()
            
    def shift_dates(self):
        selected_rows = set(item.row() for item in self.grid.selectedItems())
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "Selection Error", "Please select exactly one milestone to shift.")
            return
            
        r = list(selected_rows)[0]
        id_item = self.grid.item(r, 0)
        if not id_item: return
        mid = int(id_item.text())
        
        dialog = ShiftDatesDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            days = dialog.days_spin.value()
            if days == 0: return
            
            from ut_vfx.core.infra.database_manager import database_manager
            # Recursive shift function
            def shift_downstream(current_id, shift_days):
                # Shift current
                query = f"UPDATE prod_scheduling SET start_date = start_date + INTERVAL '{shift_days} days', end_date = end_date + INTERVAL '{shift_days} days' WHERE id = {current_id}"
                database_manager.execute_query(query, fetch=False)
                # Find children
                children = database_manager.execute_query(f"SELECT id FROM prod_scheduling WHERE depends_on_id = {current_id}") or []
                for c in children:
                    shift_downstream(c.get('id'), shift_days)
                    
            shift_downstream(mid, days)
            QMessageBox.information(self, "Success", f"Shifted milestone {mid} and all its dependencies by {days} days.")
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
