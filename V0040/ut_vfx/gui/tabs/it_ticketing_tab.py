import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QDialog, QFormLayout, QTextEdit, QAbstractItemView, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from ut_vfx.core.infra.database_manager import database_manager

class AddLogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add IT Log Entry")
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.cat_cb = QComboBox()
        self.cat_cb.addItems(["Hardware Repair", "Software Install/Fix", "Network Troubleshooting", "Access Management", "Other Activity"])
        self.cat_cb.setStyleSheet("background: #2d2d2d; padding: 4px; color: white;")
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Describe the activity performed...")
        self.desc_input.setStyleSheet("background: #2d2d2d; color: white; padding: 4px;")
        
        form.addRow("Category:", self.cat_cb)
        form.addRow("Description:", self.desc_input)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        submit_btn = QPushButton("Save Log Entry")
        submit_btn.setStyleSheet("background-color: #3b82f6; font-weight: bold; padding: 6px;")
        submit_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #6b7280; font-weight: bold; padding: 6px;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(submit_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)


class TicketDetailsDialog(QDialog):
    def __init__(self, ticket_id, ticket_title, current_user, parent=None):
        super().__init__(parent)
        self.ticket_id = ticket_id
        self.current_user = current_user
        self.setWindowTitle(f"Ticket Details - {ticket_title}")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        layout = QVBoxLayout(self)
        
        # Comments List
        comments_lbl = QLabel("Discussion Thread:")
        comments_lbl.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        layout.addWidget(comments_lbl)
        
        self.comments_list = QListWidget()
        self.comments_list.setStyleSheet("""
            QListWidget { background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px; padding: 5px; }
            QListWidget::item { border-bottom: 1px solid #444; padding: 10px; margin-bottom: 5px; background: #333333; border-radius: 4px; }
        """)
        self.comments_list.setWordWrap(True)
        layout.addWidget(self.comments_list)
        
        self.load_comments()
        
        # New Comment Input
        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Type a new comment...")
        self.comment_input.setFixedHeight(80)
        self.comment_input.setStyleSheet("background: #2d2d2d; color: white; padding: 4px; border: 1px solid #555;")
        layout.addWidget(self.comment_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        add_btn = QPushButton("Post Comment")
        add_btn.setStyleSheet("background-color: #10B981; font-weight: bold; padding: 6px 15px;")
        add_btn.clicked.connect(self.post_comment)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #6b7280; font-weight: bold; padding: 6px 15px;")
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def load_comments(self):
        self.comments_list.clear()
        query = f"SELECT author, comment_text, timestamp FROM it_ticket_comments WHERE ticket_id = {self.ticket_id} ORDER BY id ASC"
        comments = database_manager.execute_query(query) or []
        
        if not comments:
            item = QListWidgetItem("No comments yet. Be the first to comment!")
            item.setForeground(QColor("#aaaaaa"))
            self.comments_list.addItem(item)
            return
            
        for c in comments:
            author = c.get('author', 'Unknown')
            text = c.get('comment_text', '')
            ts = c.get('timestamp', '')
            
            display_text = f"[{ts}] {author} wrote:\n{text}"
            item = QListWidgetItem(display_text)
            self.comments_list.addItem(item)

    def post_comment(self):
        text = self.comment_input.toPlainText().strip()
        if not text: return
        text_esc = text.replace("'", "''")
        
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        query = f"INSERT INTO it_ticket_comments (ticket_id, author, comment_text, timestamp) VALUES ({self.ticket_id}, '{self.current_user}', '{text_esc}', '{now}')"
        if database_manager.execute_query(query, fetch=False):
            self.comment_input.clear()
            self.load_comments()
            self.comments_list.scrollToBottom()
        else:
            QMessageBox.warning(self, "Error", "Failed to post comment.")


class ItTicketingTab(QWidget):
    def __init__(self, user_role="Artist", user_data=None, parent=None):
        super().__init__(parent)
        self.user_role = user_role
        self.user_data = user_data or {}
        self.current_user = self.user_data.get("username", "Unknown")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.build_ui(main_layout)

    def build_ui(self, main_layout):
        header_title = QLabel("IT Daily Logbook")
        header_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white;")
        main_layout.addWidget(header_title)
        
        desc_label = QLabel("Record and track daily IT operations and activities.")
        desc_label.setStyleSheet("color: #aaa;")
        main_layout.addWidget(desc_label)
        
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Category Filter:"))
        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["All", "Hardware Repair", "Software Install/Fix", "Network Troubleshooting", "Access Management", "Other Activity"])
        self.filter_cb.setStyleSheet("background: #2d2d2d; color: white; padding: 4px; border: 1px solid #444;")
        self.filter_cb.currentTextChanged.connect(self.load_data)
        controls.addWidget(self.filter_cb)
        
        controls.addStretch()
        
        add_btn = QPushButton("Add Log Entry")
        add_btn.setStyleSheet("background-color: #10B981; color: white; padding: 6px 15px; font-weight: bold;")
        add_btn.clicked.connect(self.add_log_entry)
        controls.addWidget(add_btn)
        
        main_layout.addLayout(controls)

        self.grid = QTableWidget(0, 5)
        self.grid.setHorizontalHeaderLabels(["ID", "Date", "Logged By", "Category", "Description (Double-click to View/Comment)"])
        self.style_table(self.grid)
        self.grid.itemDoubleClicked.connect(self.open_ticket_details)
        self.load_data()
        
        self.grid.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.grid)

    def load_data(self):
        try:
            cat_filter = self.filter_cb.currentText()
            where_clause = "WHERE t.status = 'Logged'"
            if cat_filter != "All":
                where_clause += f" AND t.category = '{cat_filter}'"
                
            query = f"""
                SELECT t.id, t.resolved_at as date, t.category, t.description,
                       u.display_name, u.username
                FROM it_tickets t
                LEFT JOIN ut_users u ON t.submitted_by = u.username
                {where_clause}
                ORDER BY t.id DESC
            """
            logs = database_manager.execute_query(query) or []
        except Exception as e:
            logs = []
            
        self.grid.setRowCount(len(logs))
        for r, row in enumerate(logs):
            tid = f"LOG-{row.get('id', 0):04d}"
            submitted = row.get('display_name') or row.get('username') or "Unknown"
            
            id_item = QTableWidgetItem(tid)
            id_item.setData(Qt.ItemDataRole.UserRole, row.get('id'))
            
            self.grid.setItem(r, 0, id_item)
            self.grid.setItem(r, 1, QTableWidgetItem(str(row.get('date', ''))))
            self.grid.setItem(r, 2, QTableWidgetItem(submitted))
            self.grid.setItem(r, 3, QTableWidgetItem(str(row.get('category', ''))))
            self.grid.setItem(r, 4, QTableWidgetItem(str(row.get('description', ''))))

    def add_log_entry(self):
        dialog = AddLogDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cat = dialog.cat_cb.currentText()
            desc = dialog.desc_input.toPlainText().replace("'", "''")
            
            if not desc:
                QMessageBox.warning(self, "Error", "Description cannot be empty.")
                return
                
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            query = f"""
                INSERT INTO it_tickets (submitted_by, category, priority, description, status, resolved_at) 
                VALUES ('{self.current_user}', '{cat}', 'Info', '{desc}', 'Logged', '{now}')
            """
            if database_manager.execute_query(query, fetch=False):
                QMessageBox.information(self, "Success", "Log entry saved successfully.")
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", "Failed to save log entry.")
    def open_ticket_details(self, item):
        row = item.row()
        id_item = self.grid.item(row, 0)
        if not id_item: return
        
        ticket_id = id_item.data(Qt.ItemDataRole.UserRole)
        ticket_title = id_item.text()
        
        dialog = TicketDetailsDialog(ticket_id, ticket_title, self.current_user, self)
        dialog.exec()
    def style_table(self, table: QTableWidget):
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
