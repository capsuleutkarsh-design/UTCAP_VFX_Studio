import ast
import hashlib
from collections import defaultdict

class StructuralHashVisitor(ast.NodeVisitor):
    def __init__(self):
        self.structure = []

    def generic_visit(self, node):
        # We only record the type of the node, ignoring names, values, docstrings
        self.structure.append(type(node).__name__)
        super().generic_visit(node)

def get_structural_hash(node):
    visitor = StructuralHashVisitor()
    visitor.visit(node)
    # Filter out empty modules or tiny functions (less than 15 AST nodes)
    if len(visitor.structure) < 15:
        return None
    
    hash_input = "-".join(visitor.structure).encode('utf-8')
    return hashlib.md5(hash_input).hexdigest()

def detect_duplicates(parsed_files_dict):
    """
    Takes a dictionary of parsed file data (from ast_extractor)
    and returns a dictionary mapping filepath -> count of cloned functions.
    """
    # Map hash -> list of (filepath, func_name)
    hash_to_funcs = defaultdict(list)
    
    for rel_path, data in parsed_files_dict.items():
        tree = data.get("_raw_tree")
        if not tree:
            try:
                with open(data["filepath"], "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())
            except Exception:
                continue
            
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                shash = get_structural_hash(node)
                if shash:
                    hash_to_funcs[shash].append((rel_path, node.name))
                    
    # Now find duplicates (hashes with > 1 function)
    # Map filepath -> clone count
    file_clone_counts = defaultdict(int)
    
    for shash, funcs in hash_to_funcs.items():
        if len(funcs) > 1:
            for filepath, func_name in funcs:
                file_clone_counts[filepath] += 1
                
    return dict(file_clone_counts)
