import argparse
import os

from analysis.ast_extractor import generate_supercharged_md
from render.ui_generator import generate_expanding_html_from_md


CORE_ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_DIR = os.path.join(CORE_ENGINE_DIR, "output")


def resolve_default_project_dir(current_dir=None):
    cur_dir = current_dir or os.getcwd()
    cur_norm = cur_dir.replace("\\", "/")
    if "CORE_ENGINE" in cur_norm:
        return os.path.dirname(os.path.dirname(cur_dir))
    if "ArchPilot_V32" in cur_norm:
        return os.path.dirname(cur_dir)
    return cur_dir


def _resolve_output_files(output_dir):
    out_dir = os.path.abspath(output_dir)
    os.makedirs(out_dir, exist_ok=True)
    context_file = os.path.join(out_dir, "ai_context_map.md")
    dashboard_file = os.path.join(out_dir, "utcap_v32_db_sync.html")
    return out_dir, context_file, dashboard_file


def refresh_context(project_dir, output_dir=DEFAULT_OUTPUT_DIR):
    out_dir, context_file, _ = _resolve_output_files(output_dir)
    generate_supercharged_md(os.path.abspath(project_dir), context_file)
    return {"output_dir": out_dir, "context_file": context_file}


def build_map(project_dir, output_dir=DEFAULT_OUTPUT_DIR):
    out_dir, context_file, dashboard_file = _resolve_output_files(output_dir)
    project_abs = os.path.abspath(project_dir)

    print(f"-> [DRIVE] Project: {project_abs}")
    print(f"-> [DRIVE] Output:  {out_dir}")

    generate_supercharged_md(project_abs, context_file)
    generate_expanding_html_from_md(context_file, dashboard_file)

    print("\n[SUCCESS] V32 Engine Execution Complete!")
    print(f"Context:   {context_file}")
    print(f"Dashboard: {dashboard_file}")

    return {
        "project_dir": project_abs,
        "output_dir": out_dir,
        "context_file": context_file,
        "dashboard_file": dashboard_file,
    }


def main():
    parser = argparse.ArgumentParser(description="UTCAP V32 Architecture Map Builder")
    parser.add_argument("--dir", default=resolve_default_project_dir(), help="Project directory to analyze")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output folder for artifacts")
    args = parser.parse_args()
    build_map(args.dir, args.output)


if __name__ == "__main__":
    main()
