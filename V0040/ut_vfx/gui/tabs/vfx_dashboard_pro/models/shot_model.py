from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict

@dataclass
class DepartmentInfo:
    artist: str = ""
    bid_days: float = 0.0
    eta: Optional[str] = None
    status: str = ""
    wip_date: Optional[str] = None
    target: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return cls()
        valid_fields = {"artist", "bid_days", "eta", "status", "wip_date", "target"}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass  
class ArtistLogEntry:
    shot_id: str = ""
    artist: str = ""
    department: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: str = ""


@dataclass
class FeedbackEntry:
    date: str = ""
    source: str = ""
    text: str = ""
    logged_by: str = ""
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return cls()
        if isinstance(data, str):
            return cls(text=data)
        valid_fields = {"date", "source", "text", "logged_by"}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class Shot:
    id: int = -1 # Database ID
    shot_name: str = ""
    reel_episode: str = ""
    status: str = "WIP"
    edit_frames: float = 0.0
    scan_status: str = ""
    edit_status: str = ""
    in_os: str = ""
    shot_type: str = ""
    priority: int = 3
    is_hero: bool = False
    similar_to: List[str] = field(default_factory=list)
    sow: str = ""
    target: Optional[str] = None
    prev_version: str = ""
    curr_version: str = ""
    assigned_artist: str = ""
    artist_history: List[ArtistLogEntry] = field(default_factory=list)
    comp_dept: DepartmentInfo = field(default_factory=DepartmentInfo)
    roto_dept: DepartmentInfo = field(default_factory=DepartmentInfo)
    prep_dept: DepartmentInfo = field(default_factory=DepartmentInfo)
    dmp_dept: DepartmentInfo = field(default_factory=DepartmentInfo)
    cg_dept: DepartmentInfo = field(default_factory=DepartmentInfo)
    mgfx_dept: DepartmentInfo = field(default_factory=DepartmentInfo)
    slapcomp_dept: DepartmentInfo = field(default_factory=DepartmentInfo)
    feedback_internal: List[FeedbackEntry] = field(default_factory=list)
    feedback_client: List[FeedbackEntry] = field(default_factory=list)
    feedback_director: List[FeedbackEntry] = field(default_factory=list)
    wip_date: Optional[str] = None
    shot_done_date: Optional[str] = None
    submission_date: Optional[str] = None
    exr_submission: Optional[str] = None
    mov_submission: Optional[str] = None
    thumbnail_path: str = ""
    folder_paths: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    notes: str = ""
    _row_idx: int = field(default=0, repr=False)
    _modified: bool = field(default=False, repr=False)
    _semantic_embedding: Optional[List[float]] = field(default=None, repr=False)
    version: int = 1 # Optimistic Locking
    
    def get_latest_feedback(self):
        all_feedback = self.feedback_internal + self.feedback_client + self.feedback_director
        if not all_feedback:
            return None
        sorted_fb = sorted([f for f in all_feedback if f.date], key=lambda x: x.date, reverse=True)
        return sorted_fb[0] if sorted_fb else all_feedback[0]
    
    def get_all_artists(self):
        artists = set()
        if self.assigned_artist:
            artists.add(self.assigned_artist)
        for e in self.artist_history:
            if e.artist:
                artists.add(e.artist)
        for d in [self.comp_dept, self.roto_dept, self.prep_dept, self.dmp_dept, self.cg_dept, self.mgfx_dept, self.slapcomp_dept]:
            if d.artist:
                artists.add(d.artist)
        return list(artists)
    
    def to_dict(self):
        # Updated to_dict to include more fields and handle nested dataclasses
        return {
            "shot_name": self.shot_name, 
            "reel_episode": self.reel_episode, 
            "status": self.status,
            "edit_frames": self.edit_frames, 
            "scan_status": self.scan_status,
            "edit_status": self.edit_status,
            "in_os": self.in_os,
            "shot_type": self.shot_type, 
            "priority": self.priority,
            "is_hero": self.is_hero, 
            "similar_to": self.similar_to,
            "sow": self.sow, 
            "target": self.target,
            "prev_version": self.prev_version,
            "curr_version": self.curr_version,
            "assigned_artist": self.assigned_artist,
            "artist_history": [entry.to_dict() for entry in self.artist_history],
            "comp_dept": self.comp_dept.to_dict(),
            "roto_dept": self.roto_dept.to_dict(),
            "prep_dept": self.prep_dept.to_dict(),
            "dmp_dept": self.dmp_dept.to_dict(),
            "cg_dept": self.cg_dept.to_dict(),
            "mgfx_dept": self.mgfx_dept.to_dict(),
            "slapcomp_dept": self.slapcomp_dept.to_dict(),
            "feedback_internal": [fb.to_dict() for fb in self.feedback_internal],
            "feedback_client": [fb.to_dict() for fb in self.feedback_client],
            "feedback_director": [fb.to_dict() for fb in self.feedback_director],
            "wip_date": self.wip_date,
            "shot_done_date": self.shot_done_date,
            "submission_date": self.submission_date,
            "exr_submission": self.exr_submission,
            "mov_submission": self.mov_submission,
            "thumbnail_path": self.thumbnail_path,
            "folder_paths": self.folder_paths,
            "description": self.description,
            "notes": self.notes,
            "version": self.version
        }
    
    def matches_filter(self, search_text="", status_filter="All", priority_filter="All"):
        if search_text:
            artists = " ".join(self.get_all_artists())
            searchable = f"{self.shot_name} {self.sow} {self.description} {artists} {self.reel_episode}".lower()
            if search_text.lower() not in searchable:
                return False
        if status_filter != "All" and self.status != status_filter:
            return False
        if priority_filter != "All":
            try:
                if int(priority_filter) != self.priority:
                    return False
            except ValueError:
                pass
        return True
    
    def get_folder_path(self, department, folder_template, folder_base):
        template = folder_template.get(department.lower(), "")
        if not template:
            return ""
        path = template.format(reel=self.reel_episode, shot=self.shot_name)
        return f"{folder_base}\\{path}" if folder_base else path

    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return cls()
        
        # Handle complex nested fields
        special_fields = {
            "comp_dept": DepartmentInfo, "roto_dept": DepartmentInfo, 
            "prep_dept": DepartmentInfo, "dmp_dept": DepartmentInfo, 
            "cg_dept": DepartmentInfo, "mgfx_dept": DepartmentInfo, 
            "slapcomp_dept": DepartmentInfo
        }
        
        # Lists of objects
        list_fields = {
            "feedback_internal": FeedbackEntry,
            "feedback_client": FeedbackEntry,
            "feedback_director": FeedbackEntry,
            "artist_history": ArtistLogEntry
        }
        
        init_data = {}
        for k, v in data.items():
            if k in special_fields:
                init_data[k] = special_fields[k].from_dict(v)
            elif k in list_fields:
                # v is list of dicts
                if isinstance(v, list):
                    item_cls = list_fields[k]
                    # Data classes might not all have from_dict, check recursively
                    # ArtistLogEntry doesn't have from_dict in the file I saw?
                    # Let's simple init for data classes
                    if hasattr(item_cls, 'from_dict'):
                        init_data[k] = [item_cls.from_dict(i) for i in v]
                    else:
                        init_data[k] = [item_cls(**i) for i in v if isinstance(i, dict)]
            else:
                init_data[k] = v
                
        # Filter out unknown keys to prevent TypeError on __init__
        valid_keys = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in init_data.items() if k in valid_keys}
        
        return cls(**filtered_data)
