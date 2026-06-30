"""
UT_VFX Database Manager — unified proxy that selects SQLite or PostgreSQL backend.

Default: SQLite (standalone, zero-config).
Set "db_mode": "postgres" in client_config.json for network/studio use.
"""

import logging
from threading import RLock
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Proxy wrapper that delegates all database calls to the active backend.

    Backend selection:
      - "sqlite"   → SQLiteManager  (default, standalone)
      - "postgres" → PostgresManager (network/studio)
    """

    def __init__(self, db_path: Optional[str] = None):
        self.requested_mode = self._detect_mode()
        self.allow_fallback = self._allow_fallback()
        self.active_mode = self.requested_mode
        self.fallback_used = False
        self.bootstrap_error: str = ""

        logger.info(
            "DatabaseManager initializing (requested_mode=%s, allow_fallback=%s)",
            self.requested_mode,
            self.allow_fallback,
        )

        self.backend, self.active_mode, self.fallback_used = self._bootstrap_backend(db_path=db_path)

        # Trigger Phase 1 Auto-Migrations
        try:
            from .migrations.auto_migrate import run_auto_migrations
            logger.info("Executing Automated Database Migrations...")
            run_auto_migrations()
        except Exception as e:
            logger.error(f"Auto-migration check failed: {e}")

        if self.fallback_used:
            logger.warning(
                "Database fallback active: requested=%s -> active=%s. "
                "Running in local fallback mode (not centrally synced).",
                self.requested_mode,
                self.active_mode,
            )
        else:
            logger.info("Database backend active: %s", self.active_mode)

    @staticmethod
    def _detect_mode() -> str:
        """Read db_mode from GlobalConfig; default to 'sqlite'."""
        try:
            from .global_config import GlobalConfig
            mode = GlobalConfig.get_db_mode()
            if mode == "postgres":
                return mode
        except Exception:
            pass
        return "sqlite"

    @staticmethod
    def _allow_fallback() -> bool:
        """Read allow_db_fallback from GlobalConfig; default True for resilience."""
        try:
            from .global_config import GlobalConfig
            return bool(GlobalConfig.allow_db_fallback())
        except Exception:
            pass
        return True

    def _bootstrap_backend(self, db_path: Optional[str] = None) -> Tuple[object, str, bool]:
        """Create the requested backend and optionally fallback to sqlite."""
        mode = self.requested_mode

        if mode == "postgres":
            try:
                from .postgres_manager import PostgresManager

                backend = PostgresManager()
                # Force an eager connectivity check so startup fallback is deterministic.
                with backend.get_connection():
                    pass
                return backend, "postgres", False
            except Exception as exc:
                self.bootstrap_error = str(exc)
                logger.error("Postgres bootstrap failed: %s", exc)
                if not self.allow_fallback:
                    raise RuntimeError(
                        "Postgres initialization failed and fallback is disabled. "
                        f"Reason: {exc}"
                    ) from exc
                logger.warning("Falling back to SQLite backend.")
                from .sqlite_manager import SQLiteManager

                return SQLiteManager(db_path=db_path), "sqlite", True

        from .sqlite_manager import SQLiteManager
        return SQLiteManager(db_path=db_path), "sqlite", False

    def get_runtime_status(self) -> dict:
        """Expose DB runtime mode for UI/status surfaces."""
        return {
            "requested_mode": self.requested_mode,
            "active_mode": self.active_mode,
            "fallback_used": self.fallback_used,
            "allow_fallback": self.allow_fallback,
            "bootstrap_error": self.bootstrap_error,
        }

    def is_local_mode(self) -> bool:
        """True when app is running in sqlite fallback from requested postgres."""
        return str(self.active_mode).lower() == "sqlite" and bool(self.fallback_used)

    def runtime_context_summary(self) -> str:
        """Compact human-readable DB runtime context for logs/UI errors."""
        if self.is_local_mode():
            return "LOCAL MODE (SQLite fallback; central sync limited)"
        return f"{str(self.active_mode).upper()} MODE"

    def reload_from_config(self, db_path: Optional[str] = None) -> None:
        """Rebuild backend from latest GlobalConfig values."""
        try:
            self.force_shutdown()
        except Exception as exc:
            logger.debug("DatabaseManager reload: backend shutdown skipped: %s", exc)

        self.requested_mode = self._detect_mode()
        self.allow_fallback = self._allow_fallback()
        self.active_mode = self.requested_mode
        self.fallback_used = False
        self.bootstrap_error = ""
        self.backend, self.active_mode, self.fallback_used = self._bootstrap_backend(db_path=db_path)

    def __getattr__(self, name):
        """Delegate all unknown method calls to the backend."""
        return getattr(self.backend, name)

    def force_shutdown(self):
        """Explicitly shut down the backend."""
        if hasattr(self.backend, 'shutdown_system'):
            self.backend.shutdown_system()
        elif hasattr(self.backend, 'force_shutdown'):
            self.backend.force_shutdown()


_manager_lock = RLock()
_manager_instance: Optional[DatabaseManager] = None


def _get_manager() -> DatabaseManager:
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = DatabaseManager()
    return _manager_instance


class _DatabaseManagerProxy:
    """Lazy proxy to avoid eager DB bootstrap at import time."""

    def __getattr__(self, name):
        return getattr(_get_manager(), name)

    def __repr__(self):
        mgr = _manager_instance
        if mgr is None:
            return "<DatabaseManagerProxy(uninitialized)>"
        return f"<DatabaseManagerProxy(active_mode={mgr.active_mode}, fallback_used={mgr.fallback_used})>"


database_manager = _DatabaseManagerProxy()