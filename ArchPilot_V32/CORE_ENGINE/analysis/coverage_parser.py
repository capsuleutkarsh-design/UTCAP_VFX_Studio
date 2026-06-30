import os
import json
import subprocess

def parse_coverage(project_root):
    """
    Attempts to run 'coverage json' to get test coverage metrics.
    Returns a dictionary mapping relative file paths to coverage percentages.
    """
    coverage_file = os.path.join(project_root, ".coverage")
    if not os.path.exists(coverage_file):
        return {}

    try:
        # Run coverage json and output to a temporary file
        temp_json = os.path.join(project_root, "coverage_temp.json")
        result = subprocess.run(
            ["python", "-m", "coverage", "json", "-o", temp_json],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if not os.path.exists(temp_json):
            return {}
            
        with open(temp_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        os.remove(temp_json)
        
        file_coverage = {}
        for filepath, metrics in data.get("files", {}).items():
            # Normalize path to match relative paths used in ast_extractor
            try:
                rel_path = os.path.relpath(filepath, project_root).replace('\\', '/')
                percent = metrics.get("summary", {}).get("percent_covered", 0)
                file_coverage[rel_path] = round(percent, 2)
            except ValueError:
                continue
                
        return file_coverage
        
    except Exception as e:
        print(f"   [!] Coverage parsing failed: {e}")
        return {}
