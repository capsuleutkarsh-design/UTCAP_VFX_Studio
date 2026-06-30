import json
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from ..models.shot_model import Shot
from ut_vfx.core.infra.database_manager import DatabaseManager


class StaleDataError(Exception):
    """Raised when trying to save a shot that has been modified by another user."""


class SQLiteHandler:
    """
    Adapter compatible with ExcelHandler APIs, backed by tracking_shots/tracking_tasks.
    """

    _WRITE_ROLES = {"supervisor", "developer", "admin"}
    _DEPT_MAPPING: Tuple[Tuple[str, str], ...] = (
        ("comp_dept", "comp"),
        ("roto_dept", "roto"),
        ("prep_dept", "prep"),
        ("dmp_dept", "dmp"),
        ("cg_dept", "cg"),
        ("mgfx_dept", "mgfx"),
        ("slapcomp_dept", "slapcomp"),
    )

    def __init__(
        self,
        project_code: str,
        db_manager: DatabaseManager = None,
        user_id: int = 1,
        user_role: str = "artist",
    ):
        self.project_code = project_code
        self.user_id = int(user_id or 1)

        if isinstance(user_role, list):
            self.user_roles = [str(r).lower() for r in user_role if str(r).strip()]
            self.user_role = self.user_roles[0] if self.user_roles else "artist"
        else:
            role = str(user_role or "artist").lower()
            self.user_role = role
            self.user_roles = [role]

        from ut_vfx.core.infra.database_manager import database_manager

        self.db_manager = db_manager or database_manager

        self.notifier = None
        try:
            from ut_vfx.core.domain.notification_manager import NotificationManager

            self.notifier = NotificationManager()
        except Exception as e:
            logging.exception(f"Failed to init NotificationManager: {e}")

    def _check_permission(self):
        if not any(role in self._WRITE_ROLES for role in self.user_roles):
            raise PermissionError(f"User role(s) {self.user_roles} not authorized to make changes.")

    @staticmethod
    def _serialize_shot(shot: Shot) -> str:
        return json.dumps(asdict(shot), default=str)

    def _get_db_shot_row(self, shot_name: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT id, data_json, version
            FROM tracking_shots
            WHERE project_code=%s AND shot_name=%s
        """
        return self.db_manager.execute_query(query, (self.project_code, shot_name), fetch="one")

    @staticmethod
    def _safe_json_load(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return dict(raw)
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _build_tasks_payload(self, shot_id: int, shot: Shot) -> List[Dict[str, Any]]:
        tasks_payload = []
        for attr, dept_key in self._DEPT_MAPPING:
            dept = getattr(shot, attr)
            artist_name = dept.artist or ""
            tasks_payload.append(
                {
                    "shot_id": shot_id,
                    "department": dept_key,
                    "status": dept.status or "",
                    "artist": artist_name,
                    "artist_id": self.db_manager.get_user_id(artist_name) if artist_name else None,
                    "bid_days": dept.bid_days or 0.0,
                    "target": dept.target or dept.eta or "",
                }
            )
        return tasks_payload

    def _save_tasks_for_shot(self, shot_id: int, shot: Shot) -> bool:
        tasks_payload = self._build_tasks_payload(shot_id, shot)
        if not tasks_payload:
            return True
        result = self.db_manager.save_tracking_tasks(self.project_code, tasks_payload)
        return bool(result is None or result)

    def _apply_task_overrides(self, shot: Shot, task_map: Dict[str, Dict[str, Any]]):
        for attr, dept_key in self._DEPT_MAPPING:
            task = task_map.get(dept_key)
            if not task:
                continue
            dept = getattr(shot, attr)
            dept.status = task.get("status") or dept.status or ""
            dept.artist = task.get("artist") or task.get("artist_name") or dept.artist or ""
            dept.bid_days = float(task.get("bid_days") or 0.0)
            dept.target = task.get("target_date") or task.get("target") or dept.target or ""

        if not shot.assigned_artist and shot.comp_dept.artist:
            shot.assigned_artist = shot.comp_dept.artist

    def _set_shot_field_value(self, payload: Dict[str, Any], field: str, value) -> Tuple[Any, bool]:
        field_name = str(field or "").strip()
        if not field_name:
            return None, False

        if field_name in {"status", "overall_status"}:
            old_val = payload.get("status")
            payload["status"] = value
            comp = payload.get("comp_dept")
            if not isinstance(comp, dict):
                comp = {}
                payload["comp_dept"] = comp
            comp["status"] = value
            return old_val, old_val != value

        if field_name in {"assigned_artist", "artist"}:
            old_val = payload.get("assigned_artist")
            new_value = value or ""
            payload["assigned_artist"] = new_value
            comp = payload.get("comp_dept")
            if not isinstance(comp, dict):
                comp = {}
                payload["comp_dept"] = comp
            comp["artist"] = new_value
            return old_val, old_val != new_value

        if field_name in {"curr_version", "version"}:
            old_val = payload.get("curr_version")
            payload["curr_version"] = value
            return old_val, old_val != value

        if "." in field_name:
            parts = [p for p in field_name.split(".") if p]
            if not parts:
                return None, False
            target = payload
            for part in parts[:-1]:
                node = target.get(part)
                if not isinstance(node, dict):
                    node = {}
                    target[part] = node
                target = node
            leaf = parts[-1]
            old_val = target.get(leaf)
            target[leaf] = value
            return old_val, old_val != value

        old_val = payload.get(field_name)
        payload[field_name] = value
        return old_val, old_val != value

    def _notify_assignment(self, shot_name: str, old_artist: str, new_artist: str, dept_key: str = "comp"):
        if not self.notifier:
            return
        if new_artist and new_artist != old_artist:
            try:
                msg = f"You have been assigned to: {shot_name} ({dept_key.upper()})"
                self.notifier.add_notification(new_artist, msg, "assignment")
            except Exception as e:
                logging.debug(f"Notification failed for assignment: {e}")

    def _notify_status(self, shot_name: str, artist: str, old_status: str, new_status: str):
        if not self.notifier:
            return
        if not artist or old_status == new_status:
            return
        try:
            msg = f"Shot update: {shot_name} is now {new_status}"
            self.notifier.add_notification(artist, msg, "update")
        except Exception as e:
            logging.debug(f"Notification failed for status update: {e}")

    def _log_change(self, entity_type: str, entity_id: str, action: str, field: str, old_val, new_val):
        try:
            self.db_manager.log_change_event(
                self.project_code,
                entity_type,
                entity_id,
                self.user_id,
                action,
                field,
                old_val,
                new_val,
            )
        except Exception as e:
            logging.debug(f"History log write failed: {e}")

    def _log_shot_and_task_changes(self, shot: Shot, old_data: Dict[str, Any]):
        old_status = old_data.get("status")
        if old_status != shot.status:
            self._log_change("shot", shot.shot_name, "UPDATE", "status", old_status, shot.status)

        old_assigned = old_data.get("assigned_artist")
        if old_assigned != shot.assigned_artist:
            self._log_change("shot", shot.shot_name, "ASSIGN", "assigned_artist", old_assigned, shot.assigned_artist)
            self._notify_assignment(shot.shot_name, old_assigned or "", shot.assigned_artist or "", "comp")

        for attr, dept_key in self._DEPT_MAPPING:
            new_dept = getattr(shot, attr)
            old_dept = old_data.get(attr, {})
            if not isinstance(old_dept, dict):
                old_dept = {}

            old_dept_status = old_dept.get("status", "")
            old_dept_artist = old_dept.get("artist", "")

            if old_dept_status != new_dept.status:
                self._log_change(
                    "task",
                    f"{shot.shot_name}_{dept_key}",
                    "UPDATE",
                    f"{dept_key}_status",
                    old_dept_status,
                    new_dept.status,
                )
                self._notify_status(shot.shot_name, new_dept.artist or "", old_dept_status, new_dept.status or "")

            if old_dept_artist != new_dept.artist:
                self._log_change(
                    "task",
                    f"{shot.shot_name}_{dept_key}",
                    "ASSIGN",
                    f"{dept_key}_artist",
                    old_dept_artist,
                    new_dept.artist,
                )
                self._notify_assignment(shot.shot_name, old_dept_artist or "", new_dept.artist or "", dept_key)

    def _insert_new_shot(self, shot: Shot) -> bool:
        shot_tuple = (shot.shot_name, shot.status, shot.priority, self._serialize_shot(shot))
        return bool(self.db_manager.save_tracking_shots(self.project_code, [shot_tuple]))

    def _write_single_shot(self, shot: Shot) -> bool:
        if not shot.shot_name:
            return False

        db_row = self._get_db_shot_row(shot.shot_name)
        if not db_row:
            created = self._insert_new_shot(shot)
            if not created:
                return False
            db_row = self._get_db_shot_row(shot.shot_name)
            if not db_row:
                return False
            old_data = {}
        else:
            old_data = self._safe_json_load(db_row.get("data_json"))

        shot_id = int(db_row.get("id") or 0)
        db_version = int(db_row.get("version") or 0)
        current_version = int(getattr(shot, "version", 0) or 0)

        if current_version != 0 and db_version != 0 and current_version != db_version:
            raise StaleDataError(
                f"Shot '{shot.shot_name}' has been modified by another user. Please refresh."
            )

        lock_version = db_version
        shot.version = lock_version
        json_str = self._serialize_shot(shot)

        success = self.db_manager.update_tracking_shot_safe(
            self.project_code, shot.shot_name, json_str, lock_version
        )
        if not success:
            raise StaleDataError(
                f"Shot '{shot.shot_name}' has been modified by another user. Please refresh."
            )

        shot.version = lock_version + 1
        if shot_id:
            self._save_tasks_for_shot(shot_id, shot)
        self._log_shot_and_task_changes(shot, old_data)
        return True

    def _write_batch_shots(self, shots: List[Shot]) -> bool:
        batch_data = []
        for shot in shots:
            if not shot.shot_name:
                continue
            batch_data.append((shot.shot_name, shot.status, shot.priority, self._serialize_shot(shot)))

        if not batch_data:
            return False

        if not self.db_manager.save_tracking_shots(self.project_code, batch_data):
            return False

        # Keep relational task table in sync for board/assignment features.
        rows = self.db_manager.get_tracking_shots(self.project_code) or []
        row_by_name = {r.get("shot_name"): r for r in rows if r.get("shot_name")}

        tasks_payload = []
        for shot in shots:
            row = row_by_name.get(shot.shot_name)
            if not row:
                continue
            shot.id = int(row.get("id") or -1)
            shot.version = int(row.get("version") or shot.version or 1)
            tasks_payload.extend(self._build_tasks_payload(shot.id, shot))

        if tasks_payload:
            self.db_manager.save_tracking_tasks(self.project_code, tasks_payload)
        return True

    def read_shots(self) -> List[Shot]:
        """Fetch all shots for this project from DB and deserialize."""
        try:
            tasks = self.db_manager.get_tracking_tasks(self.project_code) or []
            tasks_by_shot: Dict[int, Dict[str, Dict[str, Any]]] = {}
            for task in tasks:
                shot_id = task.get("shot_id")
                dept = task.get("department")
                if shot_id is None or not dept:
                    continue
                tasks_by_shot.setdefault(shot_id, {})[dept] = task

            raw_data = self.db_manager.get_tracking_shots(self.project_code) or []
            shots = []
            for item in raw_data:
                try:
                    shot = Shot.from_dict(item)
                    shot.id = int(item.get("id") or -1)
                    shot.version = int(item.get("version") or shot.version or 1)
                    self._apply_task_overrides(shot, tasks_by_shot.get(shot.id, {}))
                    shots.append(shot)
                except Exception as e:
                    logging.exception(f"Failed to deserialize shot {item.get('shot_name', 'unknown')}: {e}")
            return shots
        except Exception as e:
            logging.exception(f"SQLiteHandler read_shots failed: {e}")
            return []

    def write_shots(self, shots: List[Shot]) -> bool:
        """Serialize and save shots to DB."""
        if not self.project_code:
            return False
        if not shots:
            return True

        self._check_permission()

        if len(shots) == 1:
            return self._write_single_shot(shots[0])
        return self._write_batch_shots(shots)

    def update_shot_field(self, shot_name: str, field: str, value, current_version: int) -> bool:
        """
        Updates a specific field of a shot using optimistic locking.
        """
        self._check_permission()

        try:
            row = self._get_db_shot_row(shot_name)
            if not row:
                return False

            shot_id = int(row.get("id") or 0)
            db_version = int(row.get("version") or 0)
            if int(current_version or 0) != 0 and db_version != 0 and int(current_version or 0) != db_version:
                raise StaleDataError(f"Shot '{shot_name}' has been modified. Update rejected.")

            payload = self._safe_json_load(row.get("data_json"))
            old_val, changed = self._set_shot_field_value(payload, field, value)
            if not changed:
                return True

            json_str = json.dumps(payload, default=str)
            success = self.db_manager.update_tracking_shot_safe(
                self.project_code, shot_name, json_str, db_version
            )
            if not success:
                raise StaleDataError(f"Shot '{shot_name}' has been modified. Update rejected.")

            self._log_change("shot", shot_name, "UPDATE", field, old_val, value)

            if shot_id:
                shot_obj = Shot.from_dict(payload)
                shot_obj.shot_name = shot_name
                self._save_tasks_for_shot(shot_id, shot_obj)

            if field in {"assigned_artist", "artist"}:
                self._notify_assignment(shot_name, old_val or "", str(value or ""), "comp")
            elif field in {"status", "overall_status"}:
                target_artist = payload.get("assigned_artist") or ""
                self._notify_status(shot_name, target_artist, str(old_val or ""), str(value or ""))

            return True
        except StaleDataError:
            raise
        except Exception as e:
            logging.exception(f"Granular update failed for {shot_name}: {e}")
            return False

    def create_backup(self):
        logging.info("SQLiteHandler: Database central backup covers this data.")
        return "DB_BACKUP_MANAGED_centrally"

    def debug_column_mapping(self):
        logging.info("SQLiteHandler: No column mapping (Direct Object Storage).")
