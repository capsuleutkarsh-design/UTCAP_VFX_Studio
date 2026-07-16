from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QSpinBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from ...core.infra.app_context import AppContext
import json

class AddPCDialog(QDialog):
    def __init__(self, parent=None, hub=None, edit_data=None):
        super().__init__(parent)
        self.hub = hub
        self.edit_data = edit_data
        
        if self.edit_data:
            self.setWindowTitle("Edit PC")
        else:
            self.setWindowTitle("Add New PC")
            
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.inp_name = QLineEdit()
        self.inp_user = QLineEdit()
        self.inp_cpu = QLineEdit()
        self.inp_gpu = QLineEdit()
        self.inp_ram = QLineEdit()
        self.inp_storage = QLineEdit()
        self.inp_location = QLineEdit()
        
        if self.edit_data:
            self.inp_name.setText(self.edit_data.get('machine_name', ''))
            self.inp_name.setReadOnly(True) # Usually don't change the primary key equivalent
            self.inp_user.setText(self.edit_data.get('assigned_to', ''))
            self.inp_cpu.setText(self.edit_data.get('cpu', ''))
            self.inp_gpu.setText(self.edit_data.get('gpu', ''))
            self.inp_ram.setText(self.edit_data.get('ram', ''))
            self.inp_storage.setText(self.edit_data.get('storage', ''))
            self.inp_location.setText(self.edit_data.get('location', ''))
            
        form.addRow("Machine Name:", self.inp_name)
        form.addRow("Assigned User:", self.inp_user)
        form.addRow("CPU:", self.inp_cpu)
        form.addRow("GPU:", self.inp_gpu)
        form.addRow("RAM (e.g. 64GB):", self.inp_ram)
        form.addRow("Storage (e.g. 2TB NVMe):", self.inp_storage)
        form.addRow("Location/Dept:", self.inp_location)
        
        layout.addLayout(form)
        
        if not self.edit_data:
            btn_scan = QPushButton("Auto-fill from Live Ops (Network)")
            btn_scan.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px;")
            btn_scan.clicked.connect(self.auto_fill)
            layout.addWidget(btn_scan)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def auto_fill(self):
        machine_name = self.inp_name.text().strip()
        if not machine_name:
            QMessageBox.warning(self, "Warning", "Please enter a Machine Name to scan for.")
            return
            
        if self.hub:
            status_dir = self.hub.get_livestatus_dir()
            report_path = status_dir / f"{machine_name}.json"
            if report_path.exists():
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    self.inp_user.setText(data.get("user", ""))
                    self.inp_cpu.setText(data.get("CPU", ""))
                    self.inp_gpu.setText(data.get("GPU", ""))
                    self.inp_ram.setText(str(data.get("RAM_GB", "")) + " GB")
                    
                    drives = data.get("Drives", [])
                    if drives:
                        total_gb = sum(float(d.get("Capacity_GB", 0)) for d in drives)
                        self.inp_storage.setText(f"{total_gb:.0f} GB")
                        
                    QMessageBox.information(self, "Success", "Auto-filled data from Live Ops!")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not read Live Ops data: {e}")
            else:
                QMessageBox.warning(self, "Not Found", "No Live Ops data found for this machine. It may be offline.")


class ItInventoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_context = AppContext()
        self.hub = self.app_context.server_hub()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.build_ui(main_layout)

    def build_ui(self, main_layout):
        
        header_title = QLabel("Hardware Inventory (IT)")
        header_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white;")
        main_layout.addWidget(header_title)
        
        # Controls
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Filter by Status:"))
        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["All", "Active", "Repair", "Available"])
        self.filter_cb.setStyleSheet("background: #2d2d2d; color: white; padding: 4px; border: 1px solid #444;")
        self.filter_cb.currentTextChanged.connect(self.load_data)
        controls.addWidget(self.filter_cb)
        controls.addStretch()
        
        add_btn = QPushButton("Add PC")
        add_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 15px; font-weight: bold;")
        add_btn.clicked.connect(self.add_workstation)
        controls.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Selected")
        edit_btn.setStyleSheet("background-color: #f59e0b; color: white; padding: 6px 15px; font-weight: bold;")
        edit_btn.clicked.connect(self.edit_workstation)
        controls.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 6px 15px; font-weight: bold;")
        delete_btn.clicked.connect(self.delete_workstation)
        controls.addWidget(delete_btn)
        
        sync_btn = QPushButton("Sync from Live Ops")
        sync_btn.setStyleSheet("background-color: #10b981; color: white; padding: 6px 15px; font-weight: bold;")
        sync_btn.setToolTip("Automatically import any unknown online PCs from Live Ops")
        sync_btn.clicked.connect(self.sync_from_live_ops)
        controls.addWidget(sync_btn)
        
        main_layout.addLayout(controls)

        # Table
        self.grid = QTableWidget(0, 8)
        self.grid.setHorizontalHeaderLabels(["Machine Name", "Assigned To", "Location", "CPU", "GPU", "RAM", "Storage", "Status"])
        self.style_table(self.grid)
        self.load_data()
        
        self.grid.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        main_layout.addWidget(self.grid)

    def load_data(self):
        try:
            from ut_vfx.core.infra.database_manager import database_manager
            status_filter = self.filter_cb.currentText()
            where_clause = ""
            if status_filter != "All":
                where_clause = f"WHERE h.status = '{status_filter}'"
                
            query = f"""
                SELECT h.id, h.machine_name, h.gpu, h.cpu, h.storage, h.ram, h.status, h.location, h.assigned_to,
                       u.display_name, u.username
                FROM hardware_inventory h
                LEFT JOIN ut_users u ON h.assigned_to = u.username
                {where_clause}
                ORDER BY h.machine_name ASC
            """
            self.hardware_data = database_manager.execute_query(query) or []
        except Exception as e:
            self.hardware_data = []
            
        self.grid.setRowCount(len(self.hardware_data))
        for r, row in enumerate(self.hardware_data):
            assigned = row.get('display_name') or row.get('username') or row.get('assigned_to') or "Unassigned"
            self.grid.setItem(r, 0, QTableWidgetItem(str(row.get('machine_name', ''))))
            self.grid.setItem(r, 1, QTableWidgetItem(assigned))
            self.grid.setItem(r, 2, QTableWidgetItem(str(row.get('location', ''))))
            self.grid.setItem(r, 3, QTableWidgetItem(str(row.get('cpu', 'N/A'))))
            self.grid.setItem(r, 4, QTableWidgetItem(str(row.get('gpu', 'N/A'))))
            self.grid.setItem(r, 5, QTableWidgetItem(str(row.get('ram', 'N/A'))))
            self.grid.setItem(r, 6, QTableWidgetItem(str(row.get('storage', 'N/A'))))
            
            status_item = QTableWidgetItem(str(row.get('status', '')))
            if status_item.text() == "Active":
                status_item.setForeground(QColor("green"))
            elif status_item.text() == "Repair":
                status_item.setForeground(QColor("red"))
            self.grid.setItem(r, 7, status_item)

    def add_workstation(self):
        dialog = AddPCDialog(self, self.hub)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            mname = dialog.inp_name.text().strip()
            user = dialog.inp_user.text().strip()
            cpu = dialog.inp_cpu.text().strip()
            gpu = dialog.inp_gpu.text().strip()
            ram = dialog.inp_ram.text().strip()
            storage = dialog.inp_storage.text().strip()
            location = dialog.inp_location.text().strip()
            
            if not mname:
                return
                
            from ut_vfx.core.infra.database_manager import database_manager
            query = f"""
                INSERT INTO hardware_inventory (machine_name, type, status, assigned_to, cpu, gpu, ram, storage, location) 
                VALUES ('{mname}', 'Workstation', 'Active', '{user}', '{cpu}', '{gpu}', '{ram}', '{storage}', '{location}')
                ON CONFLICT (machine_name) DO UPDATE SET
                assigned_to = EXCLUDED.assigned_to,
                cpu = EXCLUDED.cpu,
                gpu = EXCLUDED.gpu,
                ram = EXCLUDED.ram,
                storage = EXCLUDED.storage,
                location = EXCLUDED.location,
                status = EXCLUDED.status
            """
            database_manager.execute_query(query, fetch=False)
            self.load_data()
            
    def edit_workstation(self):
        selected = self.grid.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select a PC to edit.")
            return
            
        row = selected[0].row()
        edit_data = self.hardware_data[row]
        
        dialog = AddPCDialog(self, self.hub, edit_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            mname = dialog.inp_name.text().strip()
            user = dialog.inp_user.text().strip()
            cpu = dialog.inp_cpu.text().strip()
            gpu = dialog.inp_gpu.text().strip()
            ram = dialog.inp_ram.text().strip()
            storage = dialog.inp_storage.text().strip()
            location = dialog.inp_location.text().strip()
            
            if not mname: return
            
            from ut_vfx.core.infra.database_manager import database_manager
            query = f"""
                UPDATE hardware_inventory 
                SET assigned_to='{user}', cpu='{cpu}', gpu='{gpu}', ram='{ram}', storage='{storage}', location='{location}'
                WHERE machine_name='{mname}'
            """
            database_manager.execute_query(query, fetch=False)
            self.load_data()

    def delete_workstation(self):
        selected = self.grid.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select a PC to delete.")
            return
            
        row = selected[0].row()
        edit_data = self.hardware_data[row]
        mname = edit_data.get('machine_name')
        
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete PC '{mname}'?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from ut_vfx.core.infra.database_manager import database_manager
            database_manager.execute_query(f"DELETE FROM hardware_inventory WHERE machine_name='{mname}'", fetch=False)
            self.load_data()

    def sync_from_live_ops(self):
        from ut_vfx.core.infra.database_manager import database_manager
        status_dir = self.hub.get_livestatus_dir()
        if not status_dir.exists():
            QMessageBox.warning(self, "Error", "Live Ops directory not found.")
            return
            
        added_count = 0
        for f in status_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    
                mname = data.get("ComputerName", data.get("pc_name", f.stem))
                user = data.get("user", "")
                cpu = data.get("CPU", "")
                gpu = data.get("GPU", "")
                ram = str(data.get("RAM_GB", "")) + " GB"
                
                drives = data.get("Drives", [])
                storage = ""
                if drives:
                    total_gb = sum(float(d.get("Capacity_GB", 0)) for d in drives)
                    storage = f"{total_gb:.0f} GB"
                
                query = f"""
                    INSERT INTO hardware_inventory (machine_name, type, status, assigned_to, cpu, gpu, ram, storage) 
                    VALUES ('{mname}', 'Workstation', 'Active', '{user}', '{cpu}', '{gpu}', '{ram}', '{storage}')
                    ON CONFLICT (machine_name) DO UPDATE SET
                    cpu = EXCLUDED.cpu,
                    gpu = EXCLUDED.gpu,
                    ram = EXCLUDED.ram,
                    storage = EXCLUDED.storage
                """
                database_manager.execute_query(query, fetch=False)
                added_count += 1
            except Exception as e:
                pass
                
        QMessageBox.information(self, "Sync Complete", f"Synchronized {added_count} PCs from Live Ops network.")
        self.load_data()

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
