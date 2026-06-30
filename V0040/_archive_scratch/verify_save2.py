import sys
import os
import json
from datetime import datetime

sys.path.insert(0, 'D:/Soft/UTCAP/V0040')

from ut_vfx.core.infra.global_config import global_config
global_config.DATABASE_MODE = 'postgres'

from ut_vfx.core.infra.postgres_manager import PostgresManager
from ut_vfx.core.infra.sqlite_handler import SQLiteHandler
from ut_vfx.models.shot_model import Shot

def main():
    print("Starting test...")
    db = PostgresManager()
    
    # 1. Fetch current row
    q_fetch = "SELECT id, data_json, version FROM tracking_shots WHERE project_code=%s AND shot_name=%s"
    row = db.execute_query(q_fetch, ('UT98', 'UT98_SH_0030'), fetch="one")
    print(f"Row: {row}")
    if not row:
        return
        
    data = json.loads(row['data_json']) if isinstance(row['data_json'], str) else row['data_json']
    current_version = row['version']
    print(f"Current version: {current_version}")
    
    # 2. Try the exact update_tracking_shot_safe code
    timestamp = datetime.now().isoformat()
    q_update = """
        UPDATE tracking_shots 
        SET data_json=%s, last_updated=%s, version=version+1
        WHERE project_code=%s AND shot_name=%s AND version=%s
    """
    
    print("Running execute_query with fetch='rowcount'")
    try:
        result = db.execute_query(q_update, (json.dumps(data), timestamp, 'UT98', 'UT98_SH_0030', current_version), fetch="rowcount")
        print(f"Raw result: {result} (type: {type(result)})")
        
        is_success = result > 0
        print(f"is_success: {is_success}")
    except Exception as e:
        print(f"EXCEPTION CAUGHT IN SCRIPT: {e}")

if __name__ == '__main__':
    main()
