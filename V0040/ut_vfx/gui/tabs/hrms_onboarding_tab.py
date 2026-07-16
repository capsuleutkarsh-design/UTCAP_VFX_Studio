from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

class HrmsOnboardingTab(QWidget):
    def __init__(self, user_role="Artist", user_data=None, parent=None):
        super().__init__(parent)
        self.user_role = user_role
        self.user_data = user_data or {}
        self.is_manager = self.user_role.lower() in ["hr", "admin", "supervisor", "developer"]
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        header_title = QLabel("Onboarding Workflows (HRMS)")
        header_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white;")
        main_layout.addWidget(header_title)

        if self.is_manager:
            self.build_manager_view(main_layout)
        else:
            self.build_employee_view(main_layout)

    def style_table(self, table: QTableWidget):
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget { 
                background-color: #1e1e1e; 
                color: #e0e0e0; 
                gridline-color: #333333; 
                border: 1px solid #333; 
                font-size: 12px;
            }
            QTableWidget::item:alternate { background-color: #252525; }
            QTableWidget::item:selected { background-color: #005a9e; color: white; }
            QHeaderView::section { 
                background-color: #2d2d2d; 
                color: #aaa; 
                border: 1px solid #333; 
                padding: 4px; 
                font-weight: bold;
            }
        """)

    def build_employee_view(self, main_layout):
        title = QLabel("My Onboarding Checklist")
        title.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #00b4d8;")
        main_layout.addWidget(title)
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #444; border-radius: 4px; text-align: center; color: white; font-weight: bold; }
            QProgressBar::chunk { background-color: #10B981; }
        """)
        main_layout.addWidget(self.progress)

        self.grid = QTableWidget(0, 6)
        self.grid.setHorizontalHeaderLabels(["[x]", "Candidate", "Role", "Stage", "Start Date", "Action"])
        self.style_table(self.grid)
        self.load_employee_data()
        
        self.grid.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        main_layout.addWidget(self.grid)
        
        btn_mark = QPushButton("Mark Selected as Complete")
        btn_mark.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px; font-weight: bold; max-width: 250px;")
        btn_mark.clicked.connect(self.mark_complete)
        main_layout.addWidget(btn_mark, alignment=Qt.AlignmentFlag.AlignRight)

    def load_employee_data(self):
        try:
            from ut_vfx.core.infra.database_manager import database_manager
            query = f"""
                SELECT o.id, o.task_name, o.department, o.is_completed, u.display_name, u.job_title, u.username
                FROM onboarding_workflows o
                LEFT JOIN ut_users u ON o.user_id = u.username
                WHERE o.user_id = '{self.user_data.get("username", "")}'
            """
            tasks = database_manager.execute_query(query) or []
        except Exception as e:
            tasks = []
            
        self.grid.setRowCount(len(tasks))
        
        completed_count = 0
        for r, row in enumerate(tasks):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if row.get('is_completed') else Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, row.get('id'))
            self.grid.setItem(r, 0, chk)
            self.grid.setItem(r, 1, QTableWidgetItem(row.get('display_name', row.get('username', 'Unknown'))))
            self.grid.setItem(r, 2, QTableWidgetItem(row.get('job_title', 'General')))
            self.grid.setItem(r, 3, QTableWidgetItem(str(row.get('task_name', ''))))
            self.grid.setItem(r, 4, QTableWidgetItem(str(row.get('department', ''))))
            
            if row.get('is_completed'):
                completed_count += 1
                
            btn = QPushButton("View Details")
            btn.setStyleSheet("""
                QPushButton { background: #3a3a4a; border-radius: 4px; padding: 4px; color: white; }
                QPushButton:hover { background: #4a4a5a; }
            """)
            btn.clicked.connect(lambda _, t=row.get('task_name', ''): QMessageBox.information(self, "Task Info", f"Task: {t}\n\nPlease complete this task as part of your onboarding process."))
            self.grid.setCellWidget(r, 5, btn)
            
        if len(tasks) > 0:
            self.progress.setValue(int((completed_count / len(tasks)) * 100))
        else:
            self.progress.setValue(0)

    def mark_complete(self):
        from ut_vfx.core.infra.database_manager import database_manager
        selected_ids = []
        for r in range(self.grid.rowCount()):
            chk = self.grid.item(r, 0)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                req_id = chk.data(Qt.ItemDataRole.UserRole)
                if req_id:
                    selected_ids.append(str(req_id))
        
        if not selected_ids:
            QMessageBox.warning(self, "Warning", "No tasks selected.")
            return
            
        ids_str = ",".join(selected_ids)
        query = f"UPDATE onboarding_workflows SET is_completed = TRUE WHERE id IN ({ids_str})"
        success = database_manager.execute_query(query, fetch=False)
        if success:
            QMessageBox.information(self, "Success", f"Successfully marked {len(selected_ids)} tasks as completed.")
            self.load_employee_data()
        else:
            QMessageBox.warning(self, "Error", "Failed to update database.")
        
    def build_manager_view(self, main_layout):
        title = QLabel("Onboarding Administration")
        title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        main_layout.addWidget(title)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        def create_card(title_text, value_text, color):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #1e1e2e;
                    border-radius: 8px;
                    border-left: 4px solid {color};
                    padding: 10px;
                }}
            """)
            layout = QVBoxLayout(card)
            t_lbl = QLabel(title_text)
            t_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
            v_lbl = QLabel(value_text)
            v_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
            layout.addWidget(t_lbl)
            layout.addWidget(v_lbl)
            return card, v_lbl
            
        c_active, self.lbl_active = create_card("Total Active Workflows", "0", "#3b82f6")
        c_it, self.lbl_it_pend = create_card("IT Setup Pending", "0", "#f59e0b")
        c_hr, self.lbl_hr_pend = create_card("HR Setup Pending", "0", "#ef4444")
        c_comp, self.lbl_comp = create_card("Completed", "0", "#10b981")
        
        cards_layout.addWidget(c_active)
        cards_layout.addWidget(c_it)
        cards_layout.addWidget(c_hr)
        cards_layout.addWidget(c_comp)
        main_layout.addLayout(cards_layout)
        
        main_layout.addSpacing(15)
        
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Department Filter:"))
        self.dep_cb = QComboBox()
        self.dep_cb.addItems(["All Departments", "Compositing", "3D", "Production", "IT", "HR"])
        self.dep_cb.setStyleSheet("background: #2d2d2d; color: white; padding: 4px;")
        self.dep_cb.currentTextChanged.connect(self.load_manager_data)
        controls.addWidget(self.dep_cb)
        controls.addStretch()
        
        gen_btn = QPushButton("Generate Default Tasks")
        gen_btn.setStyleSheet("background-color: #10B981; color: white; padding: 6px 15px; font-weight: bold;")
        gen_btn.clicked.connect(self.generate_tasks)
        controls.addWidget(gen_btn)
        
        main_layout.addLayout(controls)
        
        self.manager_grid = QTableWidget(0, 7)
        self.manager_grid.setHorizontalHeaderLabels(["Emp ID", "Name", "Role", "Join Date", "HR Status", "IT Status", "Overall Progress"])
        self.style_table(self.manager_grid)
        self.load_manager_data()
        
        main_layout.addWidget(self.manager_grid)

    def generate_tasks(self):
        from ut_vfx.core.infra.database_manager import database_manager
        users = database_manager.execute_query("SELECT username FROM ut_users") or []
        for u in users:
            uid = u.get("username")
            existing = database_manager.execute_query(f"SELECT id FROM onboarding_workflows WHERE user_id = '{uid}'")
            if not existing:
                tasks = [
                    ("Submit ID Proof", "HR"),
                    ("Sign NDA", "HR"),
                    ("Setup Workstation", "IT"),
                    ("Create Email Account", "IT")
                ]
                for t, d in tasks:
                    q = f"INSERT INTO onboarding_workflows (user_id, task_name, department, is_completed) VALUES ('{uid}', '{t}', '{d}', FALSE)"
                    database_manager.execute_query(q, fetch=False)
        QMessageBox.information(self, "Success", "Generated default onboarding tasks for all users.")
        self.load_manager_data()

    def load_manager_data(self):
        try:
            from ut_vfx.core.infra.database_manager import database_manager
            query = """
                SELECT o.user_id, o.department, o.is_completed, u.display_name, u.job_title, u.id as u_id
                FROM onboarding_workflows o
                LEFT JOIN ut_users u ON o.user_id = u.username
            """
            tasks = database_manager.execute_query(query) or []
            
            users_map = {}
            hr_pending = 0
            it_pending = 0
            
            for t in tasks:
                uid = t.get('user_id')
                if uid not in users_map:
                    users_map[uid] = {
                        'u_id': t.get('u_id'),
                        'display_name': t.get('display_name'),
                        'job_title': t.get('job_title'),
                        'total': 0, 'completed': 0,
                        'hr_total': 0, 'hr_completed': 0,
                        'it_total': 0, 'it_completed': 0
                    }
                
                users_map[uid]['total'] += 1
                if t.get('is_completed'):
                    users_map[uid]['completed'] += 1
                
                dept = t.get('department')
                if dept == 'HR':
                    users_map[uid]['hr_total'] += 1
                    if t.get('is_completed'): 
                        users_map[uid]['hr_completed'] += 1
                    else:
                        hr_pending += 1
                elif dept == 'IT':
                    users_map[uid]['it_total'] += 1
                    if t.get('is_completed'): 
                        users_map[uid]['it_completed'] += 1
                    else:
                        it_pending += 1
                    
            completed_workflows = sum(1 for u in users_map.values() if u['completed'] == u['total'] and u['total'] > 0)
            active_workflows = len(users_map) - completed_workflows
            
            self.lbl_active.setText(str(active_workflows))
            self.lbl_it_pend.setText(str(it_pending))
            self.lbl_hr_pend.setText(str(hr_pending))
            self.lbl_comp.setText(str(completed_workflows))
            
            # Apply Filter
            filter_val = self.dep_cb.currentText()
            users = []
            for u in users_map.values():
                role = (u.get('job_title') or "General")
                if filter_val == "All Departments" or filter_val.lower() in str(role).lower():
                    users.append(u)
                    
        except Exception as e:
            users = []
            
        self.manager_grid.setRowCount(len(users))
        
        for r, u in enumerate(users):
            eid = f"NEW-{u.get('u_id', 0) if u.get('u_id') else 0:03d}"
            name = u.get('display_name', 'Unknown')
            role = u.get('job_title', 'General')
            jd = "N/A"
            
            hr = "Pending"
            if u['hr_total'] > 0 and u['hr_completed'] == u['hr_total']:
                hr = "Verified"
            elif u['hr_total'] == 0:
                hr = "N/A"
                
            it = "Pending"
            if u['it_total'] > 0 and u['it_completed'] == u['it_total']:
                it = "Verified"
            elif u['it_total'] == 0:
                it = "N/A"
            
            total = u.get('total', 1) or 1
            completed = u.get('completed', 0) or 0
            overall_val = int((completed / total) * 100) if total > 0 else 0
                
            self.manager_grid.setItem(r, 0, QTableWidgetItem(eid))
            self.manager_grid.setItem(r, 1, QTableWidgetItem(name))
            self.manager_grid.setItem(r, 2, QTableWidgetItem(role))
            self.manager_grid.setItem(r, 3, QTableWidgetItem(jd))
            
            hr_item = QTableWidgetItem(hr)
            if hr == "Verified": hr_item.setForeground(QColor("green"))
            elif hr == "Pending": hr_item.setForeground(QColor("orange"))
            self.manager_grid.setItem(r, 4, hr_item)
            
            it_item = QTableWidgetItem(it)
            if it == "Verified": it_item.setForeground(QColor("green"))
            elif it == "Pending": it_item.setForeground(QColor("orange"))
            self.manager_grid.setItem(r, 5, it_item)
            
            pb = QProgressBar()
            pb.setValue(overall_val)
            pb.setStyleSheet("QProgressBar { background-color: #1e1e1e; border: 1px solid #333; color: white; text-align: center; font-weight: bold; } QProgressBar::chunk { background-color: #3b82f6; }")
            self.manager_grid.setCellWidget(r, 6, pb)
