import argparse
import os

from app.server import run_server
from pipeline.map_builder import DEFAULT_OUTPUT_DIR, build_map, resolve_default_project_dir


def _resolve_default_port():
    raw = os.getenv("ARCHPILOT_PORT", "5005")
    try:
        return int(raw)
    except ValueError:
        return 5005


def main():
    parser = argparse.ArgumentParser(description="ArchPilot - UTCAP architecture map tool")
    sub = parser.add_subparsers(dest="command")

    build_cmd = sub.add_parser("build", help="Generate context map + dashboard")
    build_cmd.add_argument("--project-dir", default=resolve_default_project_dir(), help="Project directory to analyze")
    build_cmd.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output folder for generated artifacts")

    serve_cmd = sub.add_parser("serve", help="Run dashboard + AI server")
    serve_cmd.add_argument("--project-dir", default=resolve_default_project_dir(), help="Project directory to watch/analyze")
    serve_cmd.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output folder for generated artifacts")
    serve_cmd.add_argument("--host", default=os.getenv("ARCHPILOT_HOST", "0.0.0.0"), help="Server host")
    serve_cmd.add_argument("--port", type=int, default=_resolve_default_port(), help="Server port")
    serve_cmd.add_argument("--no-build", action="store_true", help="Skip build before server start")
    serve_cmd.add_argument("--no-watch", action="store_true", help="Disable filesystem watcher")

    args = parser.parse_args()
    command = args.command or "serve"

    if command == "build":
        build_map(args.project_dir, args.output)
        return

    if not getattr(args, "no_build", False):
        build_map(
            getattr(args, "project_dir", resolve_default_project_dir()),
            getattr(args, "output", DEFAULT_OUTPUT_DIR),
        )

    run_server(
        project_root=getattr(args, "project_dir", resolve_default_project_dir()),
        output_dir=getattr(args, "output", DEFAULT_OUTPUT_DIR),
        host=getattr(args, "host", os.getenv("ARCHPILOT_HOST", "0.0.0.0")),
        port=getattr(args, "port", _resolve_default_port()),
        watch=not getattr(args, "no_watch", False),
    )


if __name__ == "__main__":
    main()
