import ast
import os

def check_file(filepath):
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception as e:
        return [f"Syntax/Parse error: {e}"]
        
    for node in ast.walk(tree):
        # Bare except or catch Exception
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append(f"Line {node.lineno}: Bare 'except:' clause (swallows all errors including keyboard interrupts).")
            elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
                issues.append(f"Line {node.lineno}: Catching generic 'Exception' (hides specific failure causes).")
        
        # Missing docstrings
        elif isinstance(node, ast.FunctionDef):
            if not ast.get_docstring(node):
                issues.append(f"Line {node.lineno}: Function '{node.name}' is missing a docstring.")
            if len(node.body) > 50:
                issues.append(f"Line {node.lineno}: Function '{node.name}' is too long ({len(node.body)} statements).")
            if len(node.args.args) > 5:
                issues.append(f"Line {node.lineno}: Function '{node.name}' has too many arguments ({len(node.args.args)}).")
                
        elif isinstance(node, ast.ClassDef):
            if not ast.get_docstring(node):
                issues.append(f"Line {node.lineno}: Class '{node.name}' is missing a docstring.")
                
        # Print statements (should use logging)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'print':
                issues.append(f"Line {node.lineno}: Use of 'print()' instead of 'logging'.")
                
    return issues

def main():
    root_dirs = ['ut_vfx', 'ut_server']
    total_issues = []
    
    for d in root_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    issues = check_file(filepath)
                    for issue in issues:
                        total_issues.append(f"{filepath} - {issue}")
                        if len(total_issues) >= 150:
                            break
            if len(total_issues) >= 150:
                break
        if len(total_issues) >= 150:
            break
            
    with open('found_issues.txt', 'w', encoding='utf-8') as f:
        for issue in total_issues:
            f.write(issue + "\n")
            
    print(f"Found {len(total_issues)} issues.")

if __name__ == "__main__":
    main()
