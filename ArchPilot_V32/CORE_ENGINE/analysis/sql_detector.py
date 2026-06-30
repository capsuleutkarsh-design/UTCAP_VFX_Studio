import re
import ast

# Regex to capture the table name after FROM, JOIN, INTO, or UPDATE
SQL_TABLE_REGEX = re.compile(r'(?i)\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z0-9_]+)')

def extract_sql_tables(tree):
    """
    Walks the AST looking for string literals that appear to be SQL queries.
    Extracts and returns a unique list of database table names referenced.
    """
    tables = set()
    if not tree:
        return []
        
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value.lower()
            # Simple heuristic to identify SQL queries
            if any(k in val for k in ["select ", "insert ", "update ", "delete ", "join "]):
                matches = SQL_TABLE_REGEX.findall(node.value)
                for match in matches:
                    # Ignore common sql keywords that might get caught
                    if match.lower() not in {"select", "where", "set", "on", "and", "or", "values"}:
                        tables.add(match.lower())
                        
    return list(tables)
