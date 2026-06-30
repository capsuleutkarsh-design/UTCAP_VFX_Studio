from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List
from ..models.shot_model import Shot

class ShotTableModel(QAbstractTableModel):
    """Table model with all 19 columns from the plan"""
    
    # Column definitions: (key, header, getter_func)
    COLUMNS = [
        ("reel", "Reel/EP", lambda s: s.reel_episode or "-"),
        ("shot_name", "Shot Name", lambda s: s.shot_name),
        ("status", "Status", lambda s: s.status),
        ("artist", "Artist", lambda s: s.assigned_artist or "-"),
        ("sow", "SOW", lambda s: s.sow[:50] + "..." if len(s.sow) > 50 else s.sow or "-"),
        ("frames", "Frames", lambda s: str(int(s.edit_frames)) if s.edit_frames else "-"),
        ("target", "Target", lambda s: s.target or "-"),
        ("type", "Type", lambda s: s.shot_type or "-"),
        ("priority", "Priority", lambda s: str(s.priority)),
        ("comp", "Comp", lambda s: s.comp_dept.status or "-"),
        ("version", "Version", lambda s: s.curr_version or "-"),
        ("roto", "Roto", lambda s: s.roto_dept.status or "-"),
        ("prep", "Prep", lambda s: s.prep_dept.status or "-"),
        ("dmp", "DMP", lambda s: s.dmp_dept.status or "-"),
        ("cg", "CG", lambda s: s.cg_dept.status or "-"),
        ("mgfx", "MGFX", lambda s: s.mgfx_dept.status or "-"),
        ("in_os", "IN/OS", lambda s: s.in_os or "-"),
        ("scan", "Scan Status", lambda s: s.scan_status or "-"),
        ("edit", "Edit Status", lambda s: s.edit_status or "-"),
    ]
    
    # Status colors for visual feedback (kept for text color if needed, but background removed)
    STATUS_COLORS = {
        "APPROVED": "#2e7d32",
        "WIP": "#1976d2", 
        "RETAKE": "#f57c00",
        "SENT FOR REVIEW": "#7b1fa2",
        "YTS": "#616161",
    }
    
    def __init__(self, shots: List[Shot] = None, user_role: str = "artist"):
        super().__init__()
        self.shots = shots or []
        
        # MULTI-ROLE FIX: Handle both string and array
        if isinstance(user_role, list):
            # Extract first role if array
            self.user_role = user_role[0].lower() if user_role else "artist"
            self.user_roles = [r.lower() for r in user_role]
        else:
            # Single role string (legacy)
            self.user_role = user_role.lower()
            self.user_roles = [user_role.lower()]
        
        self.headers = [col[1] for col in self.COLUMNS]
    
    def rowCount(self, parent=QModelIndex()):
        return len(self.shots)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.shots):
            return None
        
        shot = self.shots[index.row()]
        col = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            getter = self.COLUMNS[col][2]
            return getter(shot)
        
        # Removed background color logic as per user request
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            # Center align certain columns
            if col in [5, 8, 10]:  # Frames, Priority, Version
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return None
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None
    
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        flags = super().flags(index)
        
        # RBAC: Only Sup/Dev/Admin can edit (check against all roles)
        authorized_roles = ['supervisor', 'developer', 'admin']
        # Multi-role check: user has permission if ANY of their roles match
        has_permission = any(role in authorized_roles for role in self.user_roles)
        
        if not has_permission:
            return flags # Read-only (Selectable | Enabled) by default from super
            
        # Make most columns editable except keys
        col_key = self.COLUMNS[index.column()][0]
        if col_key not in ["reel", "shot_name"]:
            flags |= Qt.ItemFlag.ItemIsEditable
            
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
            
        shot = self.shots[index.row()]
        col_key = self.COLUMNS[index.column()][0]
        
        try:
            if col_key == "status":
                shot.status = value
            elif col_key == "artist":
                shot.assigned_artist = value
            elif col_key == "sow":
                shot.sow = value
            elif col_key == "frames":
                shot.edit_frames = int(value) if value and value.isdigit() else 0
            elif col_key == "target":
                shot.target = value
            elif col_key == "type":
                shot.shot_type = value
            elif col_key == "priority":
                shot.priority = int(value) if value and value.isdigit() else 0
            elif col_key == "comp":
                shot.comp_dept.status = value
            elif col_key == "version":
                shot.curr_version = value
            elif col_key == "roto":
                shot.roto_dept.status = value
            elif col_key == "prep":
                shot.prep_dept.status = value
            elif col_key == "dmp":
                shot.dmp_dept.status = value
            elif col_key == "cg":
                shot.cg_dept.status = value
            elif col_key == "mgfx":
                shot.mgfx_dept.status = value
            elif col_key == "in_os":
                shot.in_os = value
            elif col_key == "scan":
                shot.scan_status = value
            elif col_key == "edit":
                shot.edit_status = value
                
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
            return True
        except ValueError:
            return False
            
    def update_data(self, shots: List[Shot]):
        self.beginResetModel()
        self.shots = shots
        self.endResetModel()
    
    def get_column_key(self, col_idx: int) -> str:
        if 0 <= col_idx < len(self.COLUMNS):
            return self.COLUMNS[col_idx][0]
        return ""
    
    def has_data_in_column(self, col_idx: int) -> bool:
        """Check if any shot has data in this column (for auto-hide)"""
        if not self.shots:
            return False
        getter = self.COLUMNS[col_idx][2]
        for shot in self.shots:
            val = getter(shot)
            if val and val != "-":
                return True
        return False
