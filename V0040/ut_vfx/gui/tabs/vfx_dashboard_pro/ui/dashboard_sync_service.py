import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any, Sequence

from ut_vfx.core.infra.database_manager import database_manager

from ..core.excel_handler import ExcelHandler
from ..core.kitsu_sync import KitsuSyncService


class DashboardSyncService:
    """Synchronization helpers extracted from DashboardWidget."""

    def __init__(self, project_manager):
        self.project_manager = project_manager

    @staticmethod
    def _is_local_fallback_mode() -> bool:
        try:
            status = database_manager.get_runtime_status() or {}
            active_mode = str(status.get("active_mode", "")).lower()
            return active_mode == "sqlite" and bool(status.get("fallback_used", False))
        except Exception:
            return False

    def is_excel_newer_than_db(self, project_code: str, excel_path: str) -> bool:
        """Compare Excel mtime with latest tracking_shots timestamp."""
        try:
            excel_ts = os.path.getmtime(excel_path)
            result = database_manager.execute_query(
                "SELECT MAX(last_updated) AS max_updated FROM tracking_shots WHERE project_code=%s",
                (project_code,),
                fetch="one",
            )
            if not result:
                return True

            db_val = result.get("max_updated") if isinstance(result, dict) else result[0]
            if not db_val:
                return True

            if hasattr(db_val, "timestamp"):
                db_ts = db_val.timestamp()
            else:
                db_ts = datetime.fromisoformat(str(db_val)).timestamp()
            return excel_ts > db_ts
        except Exception as exc:
            logging.debug("Excel/DB timestamp comparison failed: %s", exc)
            return False

    def sync_excel_to_database(self, project_code: str, project: Any) -> int:
        """Import Excel rows into tracking_shots and tracking_tasks."""
        excel_path = self.project_manager.get_excel_path(project_code)
        if not excel_path or not os.path.exists(excel_path):
            return 0

        try:
            excel_handler = ExcelHandler(excel_path, project)
            excel_shots = excel_handler.read_shots()
            if not excel_shots:
                return 0

            batch_data = []
            for shot in excel_shots:
                json_str = json.dumps(asdict(shot), default=str)
                batch_data.append((shot.shot_name, shot.status, shot.priority, json_str))

            if not database_manager.save_tracking_shots(project_code, batch_data):
                return 0

            rows = database_manager.get_tracking_shots(project_code) or []
            shot_id_map = {row.get("shot_name"): row.get("id") for row in rows if row.get("shot_name")}
            mapping = {
                "comp_dept": "comp",
                "roto_dept": "roto",
                "prep_dept": "prep",
                "dmp_dept": "dmp",
                "cg_dept": "cg",
                "mgfx_dept": "mgfx",
                "slapcomp_dept": "slapcomp",
            }

            tasks_payload = []
            for shot in excel_shots:
                shot_id = shot_id_map.get(shot.shot_name)
                if not shot_id:
                    continue
                for attr, dept_key in mapping.items():
                    dept = getattr(shot, attr)
                    tasks_payload.append(
                        {
                            "shot_id": shot_id,
                            "department": dept_key,
                            "status": dept.status,
                            "artist": dept.artist,
                            "artist_id": database_manager.get_user_id(dept.artist) if dept.artist else None,
                            "bid_days": dept.bid_days,
                            "target": dept.target,
                        }
                    )

            if tasks_payload:
                database_manager.save_tracking_tasks(project_code, tasks_payload)
            return len(excel_shots)
        except Exception as exc:
            logging.exception("Excel->DB sync failed for %s: %s", project_code, exc)
            return 0

    def mirror_shots_to_excel(
        self,
        shots: Sequence[Any],
        current_project: Any,
        data_handler: Any,
    ):
        """
        Write edited shots back to project Excel when DB mode is active.
        Returns (success, last_excel_mtime_or_none).
        """
        if not shots or not current_project:
            return False, None
        if isinstance(data_handler, ExcelHandler):
            return True, None

        excel_path = self.project_manager.get_excel_path(current_project.code)
        if not excel_path or not os.path.exists(excel_path):
            return False, None

        try:
            excel_handler = ExcelHandler(excel_path, current_project)
            success = bool(excel_handler.write_shots(shots))
            if success:
                return True, os.path.getmtime(excel_path)
            return False, None
        except Exception as exc:
            logging.exception("Excel mirror save failed: %s", exc)
            return False, None

    def sync_with_kitsu(self, project_name: str, local_shots: Sequence[Any]):
        """
        Pull/push dashboard shots with Kitsu.
        Returns (ok, message, cloud_shots, conflicts).
        """
        kitsu = KitsuSyncService()
        if not kitsu.connect():
            return False, kitsu.last_error or "Failed to connect to Kitsu.", [], []

        cloud_shots = kitsu.download_shots(project_name)
        if not cloud_shots:
            return False, kitsu.last_error or "No shots found on Kitsu for this project.", [], []

        local_list = list(local_shots or [])
        if local_list:
            upload_ok = kitsu.upload_shots(project_name, local_list)
            if not upload_ok:
                return False, kitsu.last_error or "Failed to upload local updates to Kitsu.", [], []

        conflicts = kitsu.find_conflicts(local_list, cloud_shots) if local_list else []
        return True, "", cloud_shots, conflicts
