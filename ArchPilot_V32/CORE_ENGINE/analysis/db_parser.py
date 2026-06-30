import os
import re


def _should_skip_root(root_path):
    parts = {p.lower() for p in root_path.replace("\\", "/").split("/") if p}
    return bool(parts.intersection({".git", "venv", ".venv", "node_modules", "__pycache__"}))


def extract_db_schema(startpath):
    print("-> [DB] Parsing SQL Schema definitions...")
    db_nodes = []

    target_sql_paths = []
    for root, dirs, files in os.walk(startpath):
        # Skip heavy folders across platforms.
        if _should_skip_root(root):
            dirs[:] = []
            continue

        if "create_indexes.sql" in files:
            target_sql_paths.append(os.path.join(root, "create_indexes.sql"))

    table_sources = {}
    for target_sql_path in target_sql_paths:
        if not os.path.exists(target_sql_path):
            continue

        with open(target_sql_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            tables = re.findall(r"ON\s+([a-zA-Z0-9_]+)\(", content, re.IGNORECASE)
            tables += re.findall(r"ANALYZE\s+([a-zA-Z0-9_]+);", content, re.IGNORECASE)
            tables += re.findall(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+)",
                content,
                re.IGNORECASE,
            )
            for table in tables:
                table_sources.setdefault(table, target_sql_path)

    for table in sorted(table_sources.keys()):
        db_nodes.append(
            {
                "id": f"db_table_{table}",
                "label": f"DB Table: {table}",
                "group": "db_table",
                "complexity": 50,  # Database nodes have fixed base complexity.
                "is_orphan": False,
                "is_entry": False,
                "true_deps": ["db_manager"],
                "classes": [],
                "funcs": [],
                "doc": f"PostgreSQL Table: {table}",
                "filepath": table_sources[table],
                "type": "database_table",
            }
        )

    return db_nodes
