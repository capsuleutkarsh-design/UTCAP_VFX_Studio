import sqlite3
import logging
import sys
from datetime import datetime
from pathlib import Path

class AttendanceManager:
    """
    Local SQLite Attendance Manager - OFFLINE MODE (FUTURE FEATURE)
    
    PURPOSE:
    --------
    This class provides a local SQLite-based attendance tracking system
    that can serve as a backup/fallback when the network drive is unavailable.
    
    CURRENT STATUS:
    --------------
    **NOT ACTIVELY USED** - The application currently uses `CentralAttendance`
    for all attendance operations, which stores data in centralized JSON files
    on the network drive.
    
    FUTURE INTEGRATION:
    ------------------
    This component is reserved for implementing offline mode functionality:
    - Automatic fallback when network drive is unmapped
    - Local caching of attendance records
    - Sync mechanism to push local records to central storage when network returns
    
    ARCHITECTURE:
    ------------
    - Database: %LOCALAPPDATA%/UTVFX/ut_vfx.db
    - Table: attendance (user_id, clock_in, clock_out, duration, date)
    - No duplicate clock-ins on same day
    
    NOTE: Kept in codebase for future offline mode implementation.
          Do not remove without consulting team lead.
    """
    def __init__(self):
        # Determine DB Path safely
        import os
        if sys.platform == "win32":
            self.db_dir = Path(os.environ.get('LOCALAPPDATA', Path.home() / "AppData" / "Local")) / "UTVFX"
        else:
            self.db_dir = Path.home() / ".ut_vfx"
            
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "ut_vfx.db"
        
        self.init_table()

    def _connect(self):
        """Create a fresh connection to the DB."""
        return sqlite3.connect(str(self.db_path))

    def execute_query(self, query, params=()):
        """Safe execution helper."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception as e:
            logging.exception(f"Attendance DB Write Error: {e}")

    def fetch_one(self, query, params=()):
        """Safe fetch helper."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            logging.exception(f"Attendance DB Read Error: {e}")
            return None

    def init_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_name TEXT,
            pc_name TEXT,
            clock_in_time TIMESTAMP,
            clock_out_time TIMESTAMP,
            duration TEXT,
            date TEXT
        )
        """
        self.execute_query(query)

    def clock_in(self, user_id, user_name, pc_name):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        # Check if already clocked in
        check_q = "SELECT id FROM attendance WHERE user_id = ? AND date = ? AND clock_out_time IS NULL"
        if self.fetch_one(check_q, (user_id, date_str)):
            logging.info(f"User {user_id} already clocked in.")
            return

        query = """
        INSERT INTO attendance (user_id, user_name, pc_name, clock_in_time, date)
        VALUES (?, ?, ?, ?, ?)
        """
        self.execute_query(query, (user_id, user_name, pc_name, now, date_str))
        logging.info(f"[TIME] CLOCK IN: {user_name}")

    def clock_out(self, user_id):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        find_q = "SELECT id, clock_in_time FROM attendance WHERE user_id = ? AND date = ? AND clock_out_time IS NULL"
        record = self.fetch_one(find_q, (user_id, date_str))
        
        if record:
            record_id, clock_in_str = record
            try:
                # Handle ISO format string vs datetime object
                if isinstance(clock_in_str, str):
                    clock_in = datetime.fromisoformat(clock_in_str)
                else:
                    clock_in = clock_in_str
                duration = str(now - clock_in).split('.')[0]
            except Exception:
                duration = "00:00:00"

            update_q = "UPDATE attendance SET clock_out_time = ?, duration = ? WHERE id = ?"
            self.execute_query(update_q, (now, duration, record_id))
            logging.info(f"[STOP] CLOCK OUT: {user_id}")