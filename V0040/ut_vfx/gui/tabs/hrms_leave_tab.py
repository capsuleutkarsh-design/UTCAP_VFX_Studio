import sys
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QFormLayout, QLineEdit, QDateEdit, QComboBox, QTextEdit, QCheckBox,
    QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QIcon
from ut_vfx.core.infra.database_manager import database_manager

class HrmsLeaveTab(QWidget):
    def __init__(self, user_role="Artist", user_data=None, parent=None):
        super().__init__(parent)
        self.user_role = user_role
        self.user_data = user_data or {}
        self.is_manager = self.user_role.lower() in ["hr", "admin", "supervisor", "developer"]
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        header_title = QLabel("Leave Management (HRMS)")
        header_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white;")
        main_layout.addWidget(header_title)

        if self.is_manager:
            self.build_manager_view(main_layout)
        else:
            self.splitter = QSplitter(Qt.Orientation.Horizontal)
            self.build_employee_view()
            main_layout.addWidget(self.splitter)

    def style_table(self, table: QTableWidget):
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget { background-color: #1e1e1e; color: #e0e0e0; gridline-color: #333333; border: 1px solid #333; font-size: 12px; }
            QTableWidget::item:alternate { background-color: #252525; }
            QTableWidget::item:selected { background-color: #005a9e; color: white; }
            QHeaderView::section { background-color: #2d2d2d; color: #aaa; border: 1px solid #333; padding: 4px; font-weight: bold; }
        """)

    def build_employee_view(self):
        left_panel = QFrame()
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(0, 0, 10, 0)

        bal_label = QLabel("Leave Balances")
        bal_label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        bal_label.setStyleSheet("color: #00b4d8;")
        left_lay.addWidget(bal_label)

        self.bal_table = QTableWidget(4, 5)
        self.bal_table.setHorizontalHeaderLabels(["Leave Type", "Opening", "Accrued", "Availed", "Balance"])
        self.style_table(self.bal_table)
        self.bal_table.setFixedHeight(150)
        left_lay.addWidget(self.bal_table)
        
        self.load_leave_balances()

        app_label = QLabel("Apply for Leave")
        app_label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        app_label.setStyleSheet("color: #00b4d8; margin-top: 15px;")
        left_lay.addWidget(app_label)
        
        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333; padding: 10px;")
        form_lay = QFormLayout(form_frame)
        form_lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        style = "background: #2d2d2d; color: white; border: 1px solid #444; padding: 4px;"
        
        self.leave_type_cb = QComboBox()
        self.leave_type_cb.addItems(["Casual Leave (CL)", "Sick Leave (SL)", "Earned Leave (EL)", "Leave Without Pay (LWP)"])
        self.leave_type_cb.setStyleSheet(style)
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setStyleSheet(style)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setStyleSheet(style)
        
        self.half_day = QCheckBox("Half Day (First/Second Half)")
        self.half_day.setStyleSheet("color: white;")
        
        self.reason = QTextEdit()
        self.reason.setFixedHeight(60)
        self.reason.setStyleSheet(style)
        
        apply_btn = QPushButton("Submit Application")
        apply_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 6px;")
        apply_btn.clicked.connect(self.submit_leave_application)
        
        form_lay.addRow("Leave Type:", self.leave_type_cb)
        form_lay.addRow("Start Date:", self.start_date)
        form_lay.addRow("End Date:", self.end_date)
        form_lay.addRow("", self.half_day)
        form_lay.addRow("Reason:", self.reason)
        form_lay.addRow("", apply_btn)
        
        left_lay.addWidget(form_frame)
        left_lay.addStretch()

        right_panel = QFrame()
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(10, 0, 0, 0)
        
        hist_label = QLabel("Leave Application History")
        hist_label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        hist_label.setStyleSheet("color: #00b4d8;")
        right_lay.addWidget(hist_label)
        
        self.hist_table = QTableWidget(0, 6)
        self.hist_table.setHorizontalHeaderLabels(["App. No", "Type", "Duration", "Applied On", "Status", "Approver"])
        self.style_table(self.hist_table)
        
        self.load_employee_data()
        
        right_lay.addWidget(self.hist_table)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([400, 600])

    def load_leave_balances(self):
        user_id = self.user_data.get("username", "")
        if not user_id: return
        
        query = f"SELECT * FROM leave_balances WHERE user_id = '{user_id}'"
        res = database_manager.execute_query(query)
        if not res:
            database_manager.execute_query(f"INSERT INTO leave_balances (user_id) VALUES ('{user_id}')", fetch=False)
            res = database_manager.execute_query(query)
            
        bal = res[0] if res else {"cl_balance": 0.0, "sl_balance": 0.0, "el_balance": 0.0, "lwp_balance": 0.0}
        
        types = [
            ("Casual Leave (CL)", 10.0, bal.get('cl_balance', 0.0)),
            ("Sick Leave (SL)", 5.0, bal.get('sl_balance', 0.0)),
            ("Earned Leave (EL)", 5.0, bal.get('el_balance', 0.0)),
            ("Leave Without Pay (LWP)", 0.0, bal.get('lwp_balance', 0.0))
        ]
        
        for i, (t_name, opening, current) in enumerate(types):
            availed = opening - current
            self.bal_table.setItem(i, 0, QTableWidgetItem(t_name))
            self.bal_table.setItem(i, 1, QTableWidgetItem(f"{opening:.1f}"))
            self.bal_table.setItem(i, 2, QTableWidgetItem("0.0")) # accrued placeholder
            self.bal_table.setItem(i, 3, QTableWidgetItem(f"{availed:.1f}"))
            self.bal_table.setItem(i, 4, QTableWidgetItem(f"{current:.1f}"))

    def submit_leave_application(self):
        type_str = self.leave_type_cb.currentText()
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        hd = 1 if self.half_day.isChecked() else 0
        rsn = self.reason.toPlainText().replace("'", "''")
        
        query = f"""
            INSERT INTO leave_requests (user_id, type, start_date, end_date, half_day, reason, status)
            VALUES ('{self.user_data.get("username", "unknown")}', '{type_str}', '{start}', '{end}', {hd}, '{rsn}', 'Pending')
        """
        if database_manager.execute_query(query, fetch=False):
            QMessageBox.information(self, "Success", "Leave application submitted successfully.")
            self.load_employee_data()
            self.reason.clear()
            self.half_day.setChecked(False)
        else:
            QMessageBox.warning(self, "Error", "Failed to submit leave application.")

    def load_employee_data(self):
        query = f"""
            SELECT lr.id, lr.type, lr.start_date, lr.end_date, lr.half_day, lr.status, lr.approved_by
            FROM leave_requests lr
            WHERE lr.user_id = '{self.user_data.get("username", "")}'
            ORDER BY lr.start_date DESC
            LIMIT 50
        """
        history = database_manager.execute_query(query) or []
        
        self.hist_table.setRowCount(len(history))
        for r, row in enumerate(history):
            self.hist_table.setItem(r, 0, QTableWidgetItem(f"LV-{row.get('id', '')}"))
            self.hist_table.setItem(r, 1, QTableWidgetItem(str(row.get('type', ''))))
            
            sd = row.get('start_date', '')
            ed = row.get('end_date', '')
            hd = row.get('half_day', 0)
            
            sd_str = str(sd).split()[0] if sd else ""
            ed_str = str(ed).split()[0] if ed else ""
            s_qdate = QDate.fromString(sd_str, "yyyy-MM-dd")
            e_qdate = QDate.fromString(ed_str, "yyyy-MM-dd")
            days = 0.5 if hd else float(s_qdate.daysTo(e_qdate) + 1)
            
            self.hist_table.setItem(r, 2, QTableWidgetItem(f"{sd} to {ed} ({days}d)"))
            self.hist_table.setItem(r, 3, QTableWidgetItem(str(sd)))
            self.hist_table.setItem(r, 4, QTableWidgetItem(str(row.get('status', ''))))
            self.hist_table.setItem(r, 5, QTableWidgetItem(str(row.get('approved_by', ''))))

    def build_manager_view(self, main_layout):
        title = QLabel("Leave Requests (Manager)")
        title.setFont(QFont("Inter", 16))
        title.setStyleSheet("color: white; font-weight: bold;")
        main_layout.addWidget(title)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        def create_card(title_text, value_text, color):
            card = QFrame()
            card.setStyleSheet(f"background-color: #1e1e2e; border-radius: 8px; border-left: 4px solid {color}; padding: 10px;")
            layout = QVBoxLayout(card)
            t_lbl = QLabel(title_text)
            t_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
            v_lbl = QLabel(value_text)
            v_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
            layout.addWidget(t_lbl)
            layout.addWidget(v_lbl)
            return card, v_lbl
            
        card_total, self.lbl_total_req = create_card("Total Requests", "0", "#3b82f6")
        card_pending, self.lbl_pending_req = create_card("Pending Approval", "0", "#f59e0b")
        card_approved, self.lbl_approved_req = create_card("Approved", "0", "#10b981")
        card_today, self.lbl_today_leave = create_card("On Leave Today", "0", "#8b5cf6")
        
        cards_layout.addWidget(card_total)
        cards_layout.addWidget(card_pending)
        cards_layout.addWidget(card_approved)
        cards_layout.addWidget(card_today)
        main_layout.addLayout(cards_layout)
        
        main_layout.addSpacing(15)

        controls = QHBoxLayout()
        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["All Departments", "3D", "Compositing", "Production", "IT"])
        self.filter_cb.setStyleSheet("padding: 4px; border-radius: 4px; background: #2a2a3a; color: white;")
        self.filter_cb.currentTextChanged.connect(self.load_manager_data)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search employee...")
        self.search_bar.setStyleSheet("padding: 4px; border-radius: 4px; background: #2a2a3a; color: white;")
        self.search_bar.setMaximumWidth(200)
        self.search_bar.textChanged.connect(self.load_manager_data)
        
        controls.addWidget(QLabel("Filter:"))
        controls.addWidget(self.filter_cb)
        controls.addWidget(self.search_bar)
        controls.addStretch()
        
        approve_btn = QPushButton("Batch Approve Selected")
        approve_btn.setStyleSheet("background-color: #10B981; color: white; padding: 4px 10px; font-weight: bold;")
        approve_btn.clicked.connect(lambda: self.batch_update_status("Approved"))
        reject_btn = QPushButton("Reject Selected")
        reject_btn.setStyleSheet("background-color: #EF4444; color: white; padding: 4px 10px; font-weight: bold;")
        reject_btn.clicked.connect(lambda: self.batch_update_status("Rejected"))
        controls.addWidget(approve_btn)
        controls.addWidget(reject_btn)
        
        main_layout.addLayout(controls)

        self.grid = QTableWidget(0, 9)
        self.grid.setHorizontalHeaderLabels(["[x]", "Employee", "Job Title", "Leave Type", "Start Date", "End Date", "Total Days", "Reason", "Status"])
        self.style_table(self.grid)
        self.load_manager_data()
        self.grid.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        main_layout.addWidget(self.grid)

    def batch_update_status(self, new_status):
        selected_ids = []
        for r in range(self.grid.rowCount()):
            chk = self.grid.item(r, 0)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                req_id = chk.data(Qt.ItemDataRole.UserRole)
                if req_id:
                    selected_ids.append(str(req_id))
        
        if not selected_ids:
            QMessageBox.warning(self, "Warning", "No requests selected.")
            return
            
        for req_id in selected_ids:
            # Fetch request
            req = database_manager.execute_query(f"SELECT * FROM leave_requests WHERE id={req_id}")
            if not req: continue
            req = req[0]
            
            if req['status'] == new_status: continue # Already processed
            
            # Collision Check
            if new_status == 'Approved' and req['status'] != 'Approved':
                user_q = database_manager.execute_query(f"SELECT job_title FROM ut_users WHERE username = '{req['user_id']}'")
                user_dept = user_q[0]['job_title'] if user_q else "General"
                
                overlap_q = f"""
                    SELECT u.display_name 
                    FROM leave_requests lr
                    JOIN ut_users u ON lr.user_id = u.username
                    WHERE lr.status = 'Approved'
                      AND u.job_title = '{user_dept}'
                      AND lr.start_date <= '{req['end_date']}'
                      AND lr.end_date >= '{req['start_date']}'
                """
                overlaps = database_manager.execute_query(overlap_q) or []
                if overlaps:
                    names = ", ".join([o.get('display_name', 'Unknown') for o in overlaps])
                    reply = QMessageBox.warning(
                        self, 
                        "Leave Collision Detected", 
                        f"Warning: The following users in the same department ({user_dept}) are already on leave during this period:\n\n{names}\n\nDo you want to proceed with approving {req['user_id']}'s leave?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        continue
            
            # Deduct balance if approving
            if new_status == 'Approved' and req['status'] != 'Approved':
                sd_str = str(req['start_date']).split()[0] if req['start_date'] else ""
                ed_str = str(req['end_date']).split()[0] if req['end_date'] else ""
                sd = QDate.fromString(sd_str, "yyyy-MM-dd")
                ed = QDate.fromString(ed_str, "yyyy-MM-dd")
                days = 0.5 if req.get('half_day') else float(sd.daysTo(ed) + 1)
                
                col_map = {"Casual Leave (CL)": "cl_balance", "Sick Leave (SL)": "sl_balance", "Earned Leave (EL)": "el_balance"}
                col = col_map.get(req['type'])
                if col:
                    # ensure user exists in balances
                    bal = database_manager.execute_query(f"SELECT * FROM leave_balances WHERE user_id = '{req['user_id']}'")
                    if not bal:
                        database_manager.execute_query(f"INSERT INTO leave_balances (user_id) VALUES ('{req['user_id']}')", fetch=False)
                    database_manager.execute_query(f"UPDATE leave_balances SET {col} = {col} - {days} WHERE user_id = '{req['user_id']}'", fetch=False)
            
            # Update status
            query = f"UPDATE leave_requests SET status = '{new_status}', approved_by = '{self.user_data.get('username', 'admin')}' WHERE id = {req_id}"
            database_manager.execute_query(query, fetch=False)
            
        QMessageBox.information(self, "Success", f"Successfully marked {len(selected_ids)} requests as {new_status}.")
        self.load_manager_data()

    def load_manager_data(self):
        query = """
            SELECT lr.id, lr.type, lr.start_date, lr.end_date, lr.status, lr.half_day, lr.reason,
                   u.display_name, u.job_title, u.username
            FROM leave_requests lr
            LEFT JOIN ut_users u ON lr.user_id = u.username
            ORDER BY lr.start_date DESC
        """
        requests = database_manager.execute_query(query) or []
        
        # Apply filters
        dept_filter = self.filter_cb.currentText()
        search_text = self.search_bar.text().lower()
        
        filtered = []
        for r in requests:
            name = (r.get('display_name') or r.get('username') or "").lower()
            job = (r.get('job_title') or "General").lower()
            
            if search_text and search_text not in name and search_text not in job:
                continue
            if dept_filter != "All Departments" and dept_filter.lower() not in job:
                continue
            filtered.append(r)
            
        requests = filtered
        
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        total_req = len(requests)
        pending_req = sum(1 for r in requests if r.get('status') == 'Pending')
        approved_req = sum(1 for r in requests if r.get('status') == 'Approved')
        today_leave = sum(1 for r in requests if r.get('status') == 'Approved' and str(r.get('start_date', '')) <= today_str <= str(r.get('end_date', '')))
        
        self.lbl_total_req.setText(str(total_req))
        self.lbl_pending_req.setText(str(pending_req))
        self.lbl_approved_req.setText(str(approved_req))
        self.lbl_today_leave.setText(str(today_leave))
            
        self.grid.setRowCount(len(requests))
        for r, row in enumerate(requests):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, row.get('id'))
            self.grid.setItem(r, 0, chk)
            self.grid.setItem(r, 1, QTableWidgetItem(row.get('display_name', row.get('username', 'Unknown'))))
            self.grid.setItem(r, 2, QTableWidgetItem(row.get('job_title', 'General')))
            self.grid.setItem(r, 3, QTableWidgetItem(str(row.get('type', ''))))
            
            sd = row.get('start_date', '')
            ed = row.get('end_date', '')
            
            sd_str = str(sd).split()[0] if sd else ""
            ed_str = str(ed).split()[0] if ed else ""
            
            s_qdate = QDate.fromString(sd_str, "yyyy-MM-dd")
            e_qdate = QDate.fromString(ed_str, "yyyy-MM-dd")
            
            # Fallback if invalid
            days = 0.5 if row.get('half_day') else (float(s_qdate.daysTo(e_qdate) + 1) if s_qdate.isValid() and e_qdate.isValid() else 1.0)
                
            self.grid.setItem(r, 4, QTableWidgetItem(sd_str))
            self.grid.setItem(r, 5, QTableWidgetItem(ed_str))
            self.grid.setItem(r, 6, QTableWidgetItem(str(days)))
            
            self.grid.setItem(r, 7, QTableWidgetItem(str(row.get('reason', ''))))
            
            status_item = QTableWidgetItem(str(row.get('status', 'Pending')))
            if status_item.text() == "Approved":
                status_item.setForeground(QColor("green"))
            elif status_item.text() == "Rejected":
                status_item.setForeground(QColor("red"))
            self.grid.setItem(r, 8, status_item)
