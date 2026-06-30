import sys
import logging
import psycopg2

sys.path.insert(0, "D:\\Soft\\UTCAP\\V0040")
from ut_vfx.core.infra.global_config import GlobalConfig

logging.basicConfig(level=logging.INFO)

def fix_schema():
    # Check if we can get password
    try:
        from ut_vfx.core.infra.postgres_manager import PostgresManager
        pm = PostgresManager()
        password = pm._load_password_secure()
    except Exception as e:
        logging.error(f"Failed to get password: {e}")
        return

    host = '127.0.0.1'
    port = 5440
    dbname = 'ut_vfx'
    user = 'postgres'

    logging.info(f"Connecting to {host}:{port}/{dbname}")
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )
    conn.autocommit = True
    cur = conn.cursor()

    try:
        cur.execute("ALTER TABLE ut_users DROP CONSTRAINT IF EXISTS ut_users_pkey CASCADE;")
        cur.execute("ALTER TABLE ut_users ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;")
        logging.info("Successfully added id column to ut_users.")
    except Exception as e:
        logging.warning(f"Failed to add id to ut_users: {e}")
        
    try:
        cur.execute("ALTER TABLE ut_roles DROP CONSTRAINT IF EXISTS ut_roles_pkey CASCADE;")
        cur.execute("ALTER TABLE ut_roles ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;")
        logging.info("Successfully added id column to ut_roles.")
    except Exception as e:
        logging.warning(f"Failed to add id to ut_roles: {e}")

if __name__ == "__main__":
    fix_schema()
