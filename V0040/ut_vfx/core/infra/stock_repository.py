"""Stock-library persistence methods — backend-agnostic (works with both PostgreSQL and SQLite)."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _is_postgres(db) -> bool:
    """Check if the db backend is PostgresManager."""
    return type(db).__name__ == "PostgresManager"


class StockRepository:
    """Stock-library persistence methods extracted from PostgresManager."""

    def __init__(self, db):
        self.db = db

    def add_stock_asset(
        self,
        path: str,
        thumb_path: str = "",
        proxy_path: str = "",
        tags: Optional[List[str]] = None,
        metadata: dict = None,
    ) -> int:
        try:
            from .global_config import GlobalConfig
            abs_p = Path(path)
            db_path = GlobalConfig.abstract_path(str(abs_p))
            tags_str = ",".join(tags) if tags and isinstance(tags, list) else (str(tags) if tags else "")
            metadata_str = json.dumps(metadata) if metadata else "{}"

            q = """
                INSERT INTO stock_library (file_path, file_name, file_size, file_type, thumb_path, proxy_path, tags, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_path) DO UPDATE SET
                    thumb_path = EXCLUDED.thumb_path,
                    proxy_path = EXCLUDED.proxy_path,
                    tags = EXCLUDED.tags
                RETURNING id
            """

            file_size = abs_p.stat().st_size if abs_p.exists() else 0
            val = (
                db_path, abs_p.name, file_size, abs_p.suffix.lower(),
                thumb_path, proxy_path, tags_str, metadata_str,
            )
            res = self.db.execute_query(q, val, fetch="lastrowid")
            if res:
                self.db.invalidate_vector_cache()
            return res or 0
        except Exception as e:
            logger.error(f"Add Stock Asset Failed: {e}")
            return 0

    def add_stock_assets_batch(self, assets_list: List[Dict[str, Any]]) -> None:
        if not assets_list:
            return
        try:
            values = []
            for asset in assets_list:
                p = Path(asset.get("file_path", ""))
                tags_str = ",".join(asset.get("tags", []))
                metadata_str = json.dumps(asset.get("metadata", {}))
                values.append((
                    str(p), p.name,
                    p.stat().st_size if p.exists() else 0,
                    p.suffix.lower(),
                    asset.get("thumb_path", ""),
                    asset.get("proxy_path", ""),
                    tags_str, metadata_str,
                ))

            if _is_postgres(self.db):
                from psycopg2.extras import execute_values
                sql = """
                    INSERT INTO stock_library (file_path, file_name, file_size, file_type, thumb_path, proxy_path, tags, metadata)
                    VALUES %s
                    ON CONFLICT (file_path) DO UPDATE SET
                        thumb_path = EXCLUDED.thumb_path,
                        proxy_path = EXCLUDED.proxy_path,
                        tags = EXCLUDED.tags,
                        metadata = EXCLUDED.metadata
                """
                with self.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        execute_values(cur, sql, values)
                        conn.commit()
            else:
                # SQLite path — use executemany with ? placeholders
                sql = """
                    INSERT INTO stock_library (file_path, file_name, file_size, file_type, thumb_path, proxy_path, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (file_path) DO UPDATE SET
                        thumb_path = excluded.thumb_path,
                        proxy_path = excluded.proxy_path,
                        tags = excluded.tags,
                        metadata = excluded.metadata
                """
                with self.db.get_connection() as conn:
                    conn.executemany(sql, values)
                    conn.commit()
        except Exception as e:
            logger.error(f"Batch add failed: {e}")
            raise

    def update_stock_asset_paths(self, asset_id, thumb_path=None, proxy_path=None, file_path=None):
        try:
            updates = []
            params = []

            if thumb_path is not None:
                updates.append("thumb_path=%s")
                params.append(thumb_path)
            if proxy_path is not None:
                updates.append("proxy_path=%s")
                params.append(proxy_path)

            if not updates:
                return

            sql = f"UPDATE stock_library SET {', '.join(updates)} WHERE "
            if asset_id:
                sql += "id=%s"
                params.append(asset_id)
            elif file_path:
                sql += "file_path=%s"
                params.append(str(file_path))
            else:
                logger.warning("update_stock_asset_paths: No ID or Path provided")
                return

            self.db.execute_query(sql, tuple(params), fetch="none")
        except Exception as e:
            logger.error(f"Failed to update asset paths: {e}")

    def update_asset_tags(self, asset_id, new_tags) -> bool:
        tags_str = ",".join(new_tags) if isinstance(new_tags, list) else new_tags
        return (
            self.db.execute_query(
                "UPDATE stock_library SET tags=%s WHERE id=%s",
                (tags_str, asset_id),
                fetch="rowcount",
            )
            > 0
        )

    def update_asset_metadata(self, asset_id, metadata_str, tags_str) -> bool:
        q = "UPDATE stock_library SET metadata=%s, tags=%s WHERE id=%s"
        result = self.db.execute_query(q, (metadata_str, tags_str, asset_id), fetch="rowcount")
        return result is not None and result > 0

    def get_stock_count(self) -> int:
        result = self.db.execute_query("SELECT COUNT(*) AS count FROM stock_library", fetch="one")
        if not result:
            return 0
        if isinstance(result, dict):
            return int(result.get("count", 0))
        return int(result[0]) if result else 0

    def get_all_stock_assets(
        self, limit=None, offset=0, search_query=None, file_types=None, asset_ids=None,
    ) -> List[Dict]:
        q = "SELECT * FROM stock_library"
        params = []
        where_clauses = []

        if asset_ids:
            placeholders = ",".join(["%s"] * len(asset_ids))
            where_clauses.append(f"id IN ({placeholders})")
            params.extend(asset_ids)

        if search_query:
            where_clauses.append("(file_name ILIKE %s OR tags ILIKE %s OR file_path ILIKE %s)")
            pattern = f"%{search_query}%"
            params.extend([pattern, pattern, pattern])

        if file_types:
            placeholders = ",".join(["%s"] * len(file_types))
            where_clauses.append(f"file_type IN ({placeholders})")
            params.extend(file_types)

        if where_clauses:
            q += " WHERE " + " AND ".join(where_clauses)

        q += " ORDER BY ingest_date DESC"
        if limit is not None:
            q += " LIMIT %s OFFSET %s"
            params.extend([int(limit), int(offset)])

        results = self.db.execute_query(q, tuple(params)) or []
        return [dict(r) for r in results]

    def get_stock_file_types(self) -> List[str]:
        q = "SELECT DISTINCT file_type FROM stock_library ORDER BY file_type"
        res = self.db.execute_query(q) or []
        return [r["file_type"] for r in res if r.get("file_type")]

    def get_stock_tags(self) -> List[str]:
        if _is_postgres(self.db):
            q = """
                SELECT DISTINCT BTRIM(unnest(string_to_array(tags, ','))) as tag
                FROM stock_library
                WHERE tags IS NOT NULL AND tags != ''
                ORDER BY tag
            """
            res = self.db.execute_query(q) or []
            return [r["tag"] for r in res if r.get("tag")]
        else:
            # SQLite: fetch all tags and split in Python
            q = "SELECT tags FROM stock_library WHERE tags IS NOT NULL AND tags != ''"
            rows = self.db.execute_query(q) or []
            tag_set = set()
            for r in rows:
                for tag in r.get("tags", "").split(","):
                    tag = tag.strip()
                    if tag:
                        tag_set.add(tag)
            return sorted(tag_set)

    def remove_stock_asset(self, asset_id) -> bool:
        try:
            if asset_id is None:
                return False
            result = self.db.execute_query(
                "DELETE FROM stock_library WHERE id=%s",
                (int(asset_id),),
                fetch="rowcount",
            )
            deleted = bool(result and result > 0)
            if deleted:
                self.db.invalidate_vector_cache()
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete stock asset by id {asset_id}: {e}")
            return False

    def remove_stock_asset_by_path(self, file_path: str) -> bool:
        try:
            if not file_path:
                return False
            result = self.db.execute_query(
                "DELETE FROM stock_library WHERE file_path=%s",
                (str(file_path),),
                fetch="rowcount",
            )
            deleted = bool(result and result > 0)
            if deleted:
                self.db.invalidate_vector_cache()
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete stock asset by path {file_path}: {e}")
            return False

    def clear_stock_library(self):
        if _is_postgres(self.db):
            self.db.execute_query("TRUNCATE TABLE stock_library RESTRICT", fetch="none")
        else:
            self.db.execute_query("DELETE FROM stock_library", fetch="none")
        self.db.invalidate_vector_cache()
        return True
