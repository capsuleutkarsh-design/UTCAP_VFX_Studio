import ast

def scan_file_for_smells(filepath, tree=None):
    """
    Performs a fast AST-based scan for common code smells and security risks.
    Returns the total count of smells found.
    """
    if tree is None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
        except Exception:
            return 0

    smell_count = 0

    for node in ast.walk(tree):
        # Bare except (Security/Bug risk)
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                smell_count += 1
        
        # Functions with too many arguments
        elif isinstance(node, ast.FunctionDef):
            if len(node.args.args) > 5:
                smell_count += 1
                
            # Long functions (rough estimate by line number if possible)
            if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                if (node.end_lineno - node.lineno) > 60:
                    smell_count += 1

        # Use of assert outside of tests
        elif isinstance(node, ast.Assert):
            if "test" not in filepath.lower():
                smell_count += 1
                
        # Use of exec or eval (Security)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec"):
                    smell_count += 1

    return smell_count
