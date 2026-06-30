import re

TODO_REGEX = re.compile(r'#\s*(TODO|FIXME|HACK|XXX)\s*[:\-]?\s*(.*)', re.IGNORECASE)

def extract_todos(filepath):
    """
    Scans a Python file for Tech Debt comments and returns a list.
    Format: [{"line": int, "type": str, "message": str}]
    """
    todos = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                match = TODO_REGEX.search(line)
                if match:
                    debt_type = match.group(1).upper()
                    message = match.group(2).strip()
                    if not message:
                        message = "No description provided."
                    todos.append({
                        "line": line_num,
                        "type": debt_type,
                        "message": message
                    })
    except Exception:
        pass
    return todos
