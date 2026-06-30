import os
import ast
import json

from .git_utils import get_git_metrics
from .db_parser import extract_db_schema
from .security_scanner import scan_file_for_smells
from .coverage_parser import parse_coverage
from .duplication_detector import detect_duplicates
from .todo_parser import extract_todos
from .sql_detector import extract_sql_tables

CACHE_VERSION = 3
CACHE_FILE_NAME = "archpilot_ast_cache.json"


def _cache_path(output_file):
    return os.path.join(os.path.dirname(os.path.abspath(output_file)), CACHE_FILE_NAME)


def _load_cache(cache_path):
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("version") != CACHE_VERSION:
            return {}
        entries = payload.get("entries", {})
        return entries if isinstance(entries, dict) else {}
    except Exception:
        return {}


def _save_cache(cache_path, entries):
    payload = {"version": CACHE_VERSION, "entries": entries}
    tmp_path = f"{cache_path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, separators=(",", ":"))
        os.replace(tmp_path, cache_path)
    except OSError:
        # Fallback for environments where atomic replace is blocked.
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, separators=(",", ":"))


def _file_signature(filepath):
    stat = os.stat(filepath)
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def _parse_python_file(filepath):
    with open(filepath, "r", encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source)

    complexity = sum(
        2 if isinstance(n, (ast.If, ast.For, ast.While, ast.FunctionDef, ast.ClassDef)) else 1
        for n in ast.walk(tree)
    )
    mod_doc = ast.get_docstring(tree) or "No module docstring provided."

    raw_imports = []
    classes_info = []
    funcs_info = []

    for item in tree.body:
        if isinstance(item, ast.Import):
            raw_imports.extend([(alias.name, 0) for alias in item.names])
        elif isinstance(item, ast.ImportFrom):
            # Handle both `from x import y` and `from . import y`
            if item.module:
                raw_imports.append((item.module, item.level))
            else:
                for alias in item.names:
                    if alias.name != "*":
                        raw_imports.append((alias.name, item.level))
        elif isinstance(item, ast.ClassDef):
            classes_info.append(
                {
                    "name": item.name,
                    "doc": ast.get_docstring(item) or "No class docstring.",
                    "line": item.lineno,
                }
            )
        elif isinstance(item, ast.FunctionDef):
            funcs_info.append(
                {
                    "name": item.name,
                    "doc": ast.get_docstring(item) or "No func docstring.",
                    "line": item.lineno,
                }
            )

    return {
        "complexity": complexity,
        "doc": mod_doc,
        "raw_imports": raw_imports,
        "classes_info": classes_info,
        "funcs_info": funcs_info,
        "_raw_tree": tree,
        "lint_count": scan_file_for_smells(filepath, tree=tree),
        "todos": extract_todos(filepath),
        "sql_tables": extract_sql_tables(tree)
    }


def _safe_parse_python_file(filepath):
    print(f"Parsing: {filepath}", flush=True)
    try:
        return _parse_python_file(filepath)
    except Exception:
        return {
            "complexity": 0,
            "doc": "Parse Error",
            "raw_imports": [],
            "classes_info": [],
            "funcs_info": [],
            "_raw_tree": None,
            "lint_count": 0,
            "todos": [],
            "sql_tables": []
        }


def detect_cycles(edges):
    adj = {}
    for src, dst in edges:
        if src not in adj: adj[src] = []
        adj[src].append(dst)
    
    cycles = set()
    def visit(node, stack, visited):
        if node in stack:
            idx = stack.index(node)
            for i in range(idx, len(stack)): cycles.add(stack[i])
            return
        if node in visited: return
        
        visited.add(node)
        stack.append(node)
        for neighbor in adj.get(node, []):
            visit(neighbor, stack, visited)
        stack.pop()

    visited_global = set()
    for node in list(adj.keys()):
        visit(node, [], visited_global)
    return cycles

def generate_supercharged_md(startpath, output_file):
    print(f"-> [1/2] Analyzing: {startpath}")
    IGNORE_FOLDERS = {
        'venv', '.venv', 'env', '.env', 'node_modules', '__pycache__', '.git',
        'build', 'dist', 'output', 'docs', '.idea', 'static', 'templates',
        'backups', 'Cache', 'logs', 'AppData', 'Documents', 'docs', 'tests',
        'migrations', 'Reference', '.pytest_cache', '.ruff_cache', '.vscode',
        '_localapp', '.pycache_tmp', '.github', 'external', 'DB', 'deployment', 'ArchPilot_V32',
        'python_portable', 'Lib', 'site-packages', 'Scripts'
    }

    module_to_file = {}
    parsed_files = {}
    cache_file = _cache_path(output_file)
    cache_entries = _load_cache(cache_file)
    next_cache_entries = {}
    cache_hits = 0
    cache_misses = 0
    
    # Load test coverage data once
    coverage_data = parse_coverage(startpath)

    for root, dirs, files in os.walk(startpath):
        dirs[:] = sorted([d for d in dirs if d not in IGNORE_FOLDERS])
        for file in sorted(files):
            if file.endswith('.py') and file != "generate_ai_map_v4.py":
                filepath = os.path.abspath(os.path.join(root, file))
                rel_path = os.path.relpath(filepath, startpath).replace('\\', '/')
                mod_name = os.path.splitext(rel_path)[0].replace('/', '.')
                module_to_file[mod_name] = rel_path
                if file == '__init__.py':
                    module_to_file[mod_name.rsplit('.', 1)[0]] = rel_path

                try:
                    sig = _file_signature(filepath)
                except OSError:
                    # File may disappear mid-scan (editor temp writes); skip this round.
                    continue
                cached = cache_entries.get(rel_path)
                if cached and cached.get("sig") == sig and isinstance(cached.get("parsed"), dict):
                    parsed_data = cached["parsed"]
                    cache_hits += 1
                else:
                    parsed_data = _safe_parse_python_file(filepath)
                    cache_misses += 1

                tree = parsed_data.pop("_raw_tree", None)
                next_cache_entries[rel_path] = {"sig": sig, "parsed": parsed_data}
                parsed_files[rel_path] = {"filepath": filepath, "mod_name": mod_name, "_raw_tree": tree, **parsed_data}

    try:
        _save_cache(cache_file, next_cache_entries)
        print(f"-> [AST] Cache: {cache_hits} hit / {cache_misses} miss ({len(next_cache_entries)} files)")
    except Exception as cache_error:
        print(f"   [!] AST cache write failed: {cache_error}")

    true_edges = set()
    for rel_path, data in parsed_files.items():
        if "raw_imports" not in data: continue
        current_mod = data["mod_name"]
        resolved_deps = set()
        
        for imp_mod, level in data["raw_imports"]:
            if not imp_mod: continue
            target = imp_mod
            if level > 0:
                base = current_mod.split('.')[:-level]
                target = ".".join(base + imp_mod.split('.')) if imp_mod else ".".join(base)
            
            res = module_to_file.get(target) or module_to_file.get(target.rsplit('.', 1)[0])
            if res and res != rel_path:
                resolved_deps.add(res)
                true_edges.add((rel_path, res))
                
        data["true_deps"] = sorted(resolved_deps)

    churn, age, authors = get_git_metrics(startpath)
    circular_nodes = detect_cycles(true_edges)

    incoming = {f: 0 for f in parsed_files}
    for src, dst in true_edges: incoming[dst] += 1
    
    # Detect clones across the whole project
    clone_counts = detect_duplicates(parsed_files)
    
    # Optional: cleanup _raw_tree from memory before writing
    for data in parsed_files.values():
        data.pop("_raw_tree", None)
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("# UTCAP Core Architecture\n")
        db_tables = extract_db_schema(startpath)
        for t in db_tables:
            out.write(f"\n## `{t['id']}`\n")
            out.write(f"FilePath: {t['filepath']}\n")
            out.write(f"ModDoc: {repr(t['doc'])}\n")
            out.write(f"Complexity: {t['complexity']}\n")
            out.write(f"IsOrphan: False\n")
            out.write(f"IsEntry: False\n")
            out.write(f"TrueDeps: `db_manager`\n")
            out.write(f"Type: database_table\n")

        for rel_path, data in parsed_files.items():
            if "complexity" not in data: continue
            is_entry = any(k in rel_path.lower() for k in ['main', 'gatekeeper', '__init__', 'run_'])
            is_orphan = (incoming.get(rel_path, 0) == 0) and not is_entry
            
            out.write(f"\n## `{rel_path}`\n")
            out.write(f"FilePath: {data['filepath']}\n")
            out.write(f"ModDoc: {repr(data['doc'])}\n")
            out.write(f"Complexity: {data.get('complexity', 0)}\n")
            out.write(f"IsOrphan: {is_orphan}\n")
            out.write(f"IsEntry: {is_entry}\n")
            out.write(f"ChurnCount: {churn.get(rel_path, 0)}\n")
            out.write(f"LastMod: {age.get(rel_path, 0)}\n")
            out.write(f"TopAuthor: {authors.get(rel_path, 'Unknown')}\n")
            out.write(f"IsCircular: {rel_path in circular_nodes}\n")
            out.write(f"LintCount: {data.get('lint_count', 0)}\n")
            out.write(f"Coverage: {coverage_data.get(rel_path, 0.0)}\n")
            out.write(f"Clones: {clone_counts.get(rel_path, 0)}\n")
            if data.get('todos'): 
                out.write(f"Todos: {json.dumps(data['todos'])}\n")
            if data.get('sql_tables'): 
                out.write(f"SqlTables: {','.join(data['sql_tables'])}\n")
            if data.get('true_deps'): out.write(f"TrueDeps: `{', '.join(data['true_deps'])}`\n")
            
            for cls_obj in data.get("classes_info", []): 
                clean_cdoc = cls_obj['doc'].replace('\n', ' ')
                out.write(f"Class `{cls_obj['name']}|||DOC|||{clean_cdoc}|||LINE|||{cls_obj['line']}` \n")
            for f_obj in data.get("funcs_info", []): 
                clean_fdoc = f_obj['doc'].replace('\n', ' ')
                out.write(f"Func `{f_obj['name']}|||DOC|||{clean_fdoc}|||LINE|||{f_obj['line']}` \n")
