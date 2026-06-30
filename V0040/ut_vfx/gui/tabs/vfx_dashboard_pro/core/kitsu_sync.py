import logging
from typing import Dict, List

try:
    import gazu
    _HAS_GAZU = True
except ImportError:
    _HAS_GAZU = False

from ut_vfx.core.infra.global_config import GlobalConfig
from ..models.shot_model import Shot, DepartmentInfo

logger = logging.getLogger(__name__)

class KitsuSyncService:
    """
    Connects to Kitsu via Gazu client and syncs the UTCAP VFX Dashboard Shot model.
    Maps Kitsu hierarchy: Project -> Sequence -> Shot -> Task
    """
    
    # Map UTCAP department keys to standard Kitsu task types
    TASK_TYPE_MAP = {
        "comp_dept": "Compositing",
        "roto_dept": "Roto",
        "prep_dept": "Prep",
        "dmp_dept": "Matte Painting",
        "cg_dept": "CG",
        "mgfx_dept": "Motion Graphics",
        "slapcomp_dept": "Slap Comp"
    }

    # Inverse map for fast lookups when pulling from Kitsu
    INV_TASK_TYPE_MAP = {v.lower(): k for k, v in TASK_TYPE_MAP.items()}

    def __init__(self, host: str = "", email: str = "", password: str = "", api_key: str = ""):
        self.host = host.strip()
        self.email = email.strip()
        self.password = password.strip()
        self.api_key = api_key.strip()
        self.last_error = ""
        self.connected = False
        
        # Internal caching to reduce API calls
        self._project = None
        self._task_types = {}
        self._task_statuses = {}

    def connect(self) -> bool:
        if not _HAS_GAZU:
            self.last_error = "gazu library is not installed. Install via: pip install gazu"
            logger.error(self.last_error)
            return False
            
        self.last_error = ""
        
        # Load from config if not explicitly passed
        raw_host = self.host or GlobalConfig.get("kitsu_url", "")
        email = self.email or GlobalConfig.get("kitsu_email", "")
        password = (
            self.password
            or self.api_key
            or GlobalConfig.get("kitsu_password", "")
            or GlobalConfig.get("kitsu_api_key", "")
        )
        
        if not raw_host or not email or not password:
            self.last_error = "Kitsu credentials not fully configured (host/email/password missing)."
            logger.warning(self.last_error)
            return False

        # Ensure correct API path
        api_host = raw_host
        if api_host.endswith("/"):
            api_host = api_host[:-1]
        if not api_host.endswith("/api"):
            api_host = f"{api_host}/api"
            
        try:
            gazu.client.set_host(api_host)
            gazu.log_in(email, password)
            self.connected = True
            
            # Cache dictionaries
            self._cache_dictionaries()
            return True
        except Exception as exc:
            self.last_error = f"Kitsu connection failed: {exc}"
            logger.error(self.last_error)
            self.connected = False
            return False

    def _cache_dictionaries(self):
        """Fetch and cache Task Types and Task Statuses to map correctly."""
        try:
            types = gazu.task.all_task_types()
            for t in types:
                self._task_types[t['name'].lower()] = t
                
            statuses = gazu.task.all_task_statuses()
            for s in statuses:
                self._task_statuses[s['name'].lower()] = s
        except Exception as e:
            logger.warning(f"Failed to cache dictionaries from Kitsu: {e}")

    def _get_status_name(self, status_id: str) -> str:
        """Helper to resolve status name from ID."""
        for s in self._task_statuses.values():
            if s['id'] == status_id:
                return s['name']
        return ""

    def download_shots(self, project_name: str) -> List[Shot]:
        """Download all shots for the matched project from Kitsu."""
        if not self.connected:
            return []

        try:
            # 1. Get Project
            project = gazu.project.get_project_by_name(project_name)
            if not project:
                self.last_error = f"Project '{project_name}' not found in Kitsu."
                logger.error(self.last_error)
                return []
                
            self._project = project
            
            # 2. Get all sequences and shots
            kitsu_sequences = {seq['id']: seq for seq in gazu.shot.all_sequences_for_project(project)}
            kitsu_shots = gazu.shot.all_shots_for_project(project)
            kitsu_tasks = gazu.task.all_tasks_for_project(project)

            # 3. Create a task lookup: shot_id -> [tasks]
            tasks_by_shot = {}
            for t in kitsu_tasks:
                if t['entity_id'] not in tasks_by_shot:
                    tasks_by_shot[t['entity_id']] = []
                tasks_by_shot[t['entity_id']].append(t)
                
            # 4. Build UTCAP Shot models
            utcap_shots = []
            for k_shot in kitsu_shots:
                seq_id = k_shot.get('parent_id')
                seq_name = kitsu_sequences[seq_id]['name'] if seq_id in kitsu_sequences else "DEFAULT"
                
                shot = Shot(
                    shot_name=k_shot['name'],
                    reel_episode=seq_name,
                    description=k_shot.get('description', ''),
                    status=k_shot.get('data', {}).get('status', 'WIP'),  # Entity level status is sometimes kept in data
                    edit_frames=float(k_shot.get('nb_frames', 0))
                )
                
                # Assign Tasks mapped to Departments
                shot_tasks = tasks_by_shot.get(k_shot['id'], [])
                for task in shot_tasks:
                    task_type = task['task_type_id']
                    
                    # Find task type name
                    task_type_name = ""
                    for name, t_obj in self._task_types.items():
                        if t_obj['id'] == task_type:
                            task_type_name = name
                            break
                            
                    dept_key = self.INV_TASK_TYPE_MAP.get(task_type_name)
                    if dept_key and hasattr(shot, dept_key):
                        # Construct DepartmentInfo
                        status_id = task['task_status_id']
                        status_name = self._get_status_name(status_id)
                        
                        dept_info = DepartmentInfo(
                            status=status_name,
                            artist="Unknown" # Advanced: need to resolve assignees with gazu.person
                        )
                        setattr(shot, dept_key, dept_info)
                        
                utcap_shots.append(shot)

            return utcap_shots

        except Exception as e:
            self.last_error = f"Gazu download error: {e}"
            logger.error(self.last_error, exc_info=True)
            return []

    def upload_shots(self, project_name: str, local_shots: List[Shot]) -> bool:
        """Push UTCAP shot attributes and task statuses to Kitsu."""
        if not self.connected:
            return False
            
        try:
            project = gazu.project.get_project_by_name(project_name)
            if not project:
                return False
                
            # Maps for resolution
            kitsu_sequences = {seq['name']: seq for seq in gazu.shot.all_sequences_for_project(project)}
            kitsu_shots = {s['name']: s for s in gazu.shot.all_shots_for_project(project)}
            
            for shot in local_shots:
                k_seq = kitsu_sequences.get(shot.reel_episode)
                if not k_seq:
                    k_seq = gazu.shot.new_sequence(project, shot.reel_episode)
                    kitsu_sequences[shot.reel_episode] = k_seq
                    
                k_shot = kitsu_shots.get(shot.shot_name)
                if not k_shot:
                    # Create shot if missing
                    k_shot = gazu.shot.new_shot(
                        project,
                        k_seq,
                        shot.shot_name,
                        nb_frames=int(shot.edit_frames or 0),
                    )
                    kitsu_shots[shot.shot_name] = k_shot
                else:
                    # Update shot metadata (frames, desc)
                    target_frames = int(shot.edit_frames or 0)
                    target_description = shot.description or ""
                    if (
                        int(k_shot.get('nb_frames') or 0) != target_frames
                        or str(k_shot.get('description') or "") != target_description
                    ):
                        # gazu.shot.update_shot expects a single updated shot dict.
                        k_shot["nb_frames"] = target_frames
                        k_shot["description"] = target_description
                        gazu.shot.update_shot(k_shot)
                
                # Sync Tasks (Departments)
                self._sync_tasks_for_shot(k_shot, shot)

            return True

        except Exception as e:
            self.last_error = f"Gazu upload error: {e}"
            logger.error(self.last_error, exc_info=True)
            return False

    def _sync_tasks_for_shot(self, k_shot: dict, shot: Shot):
        """Update or create tasks for a specific Kitsu shot."""
        existing_tasks = gazu.task.all_tasks_for_shot(k_shot)
        tasks_by_type = {t['task_type_id']: t for t in existing_tasks}
        
        for dept_key, task_type_label in self.TASK_TYPE_MAP.items():
            if not hasattr(shot, dept_key):
                continue
                
            dept_info: DepartmentInfo = getattr(shot, dept_key)
            if not dept_info or not dept_info.status:
                continue # Skip empty tasks
                
            # Find task type on Kitsu
            k_type = self._task_types.get(task_type_label.lower())
            if not k_type:
                logger.warning(f"Kitsu Task Type '{task_type_label}' not found on server.")
                continue
                
            # Find status on Kitsu
            k_status = self._task_statuses.get(dept_info.status.lower())
            if not k_status:
                continue # Unknown status to map
                
            task_type_id = k_type['id']
            k_task = tasks_by_type.get(task_type_id)
            
            if not k_task:
                # Create Task
                gazu.task.new_task(k_shot, k_type, task_status=k_status)
            else:
                # Update Status if changed
                if k_task['task_status_id'] != k_status['id']:
                    # Use gazu.task.add_comment to change status
                    gazu.task.add_comment(k_task, k_status, comment="Status synced from UTCAP")

    def find_conflicts(self, local_shots: List[Shot], cloud_shots: List[Shot]) -> List[Dict]:
        """Basic DB vs Kitsu conflict detection."""
        conflicts = []
        cloud_map = {s.shot_name: s for s in cloud_shots if s.shot_name}

        for local in local_shots:
            if not local.shot_name:
                continue
            cloud = cloud_map.get(local.shot_name)
            if not cloud:
                continue

            # Check core metadata
            is_conflict = False
            if local.description != cloud.description:
                is_conflict = True
            
            # Check department statuses
            for dept_key in self.TASK_TYPE_MAP.keys():
                if hasattr(local, dept_key) and hasattr(cloud, dept_key):
                    l_status = getattr(local, dept_key).status
                    c_status = getattr(cloud, dept_key).status
                    if l_status and c_status and l_status != c_status:
                        is_conflict = True
                        break

            if is_conflict:
                conflicts.append({
                    "shot_id": local.shot_name,
                    "local": local,
                    "cloud": cloud,
                })

        return conflicts
