import atexit
import os
import threading
import webbrowser
import queue

from flask import Flask, Response, jsonify, redirect, request, send_file
from flask_cors import CORS
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from pipeline.map_builder import DEFAULT_OUTPUT_DIR, refresh_context

CORE_ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHPILOT_DIR = os.path.dirname(CORE_ENGINE_DIR)
DEFAULT_PROJECT_ROOT = os.path.dirname(ARCHPILOT_DIR)

app = Flask(__name__)
CORS(app)

class MessageAnnouncer:
    def __init__(self):
        self.listeners = []
    def listen(self):
        q = queue.Queue(maxsize=5)
        self.listeners.append(q)
        return q
    def announce(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]

announcer = MessageAnnouncer()

WATCH_PROJECT_ROOT = DEFAULT_PROJECT_ROOT
WATCH_OUTPUT_DIR = os.path.abspath(DEFAULT_OUTPUT_DIR)

def _dashboard_file():
    return os.path.join(WATCH_OUTPUT_DIR, "utcap_v32_db_sync.html")

@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    dp = _dashboard_file()
    if os.path.exists(dp):
        return send_file(dp)
    return f"Dashboard missing at {dp}. Run: python archpilot.py build", 404

@app.route("/api/file")
def get_file_content():
    p = request.args.get("path")
    if not p: return jsonify({"error": "No path"}), 400

    project_root = os.path.realpath(WATCH_PROJECT_ROOT)
    requested_rel = os.path.normpath(p).lstrip("\\/")
    abs_p = os.path.realpath(os.path.join(project_root, requested_rel))
    abs_norm = abs_p.replace("\\", "/").lower()

    if ".env" in abs_norm or "/core_engine/" in abs_norm:
        return jsonify({"error": "Access Denied (Protected Path)"}), 403

    try:
        if os.path.commonpath([project_root.lower(), abs_p.lower()]) != project_root.lower():
            return jsonify({"error": "Access Denied"}), 403
    except ValueError:
        return jsonify({"error": "Access Denied"}), 403

    if not os.path.isfile(abs_p):
        return jsonify({"error": "Not found"}), 404

    if os.path.getsize(abs_p) > (2 * 1024 * 1024):
        return jsonify({"error": "File too large for inline view (>2MB)"}), 413

    try:
        with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
            return jsonify({"content": f.read(), "path": os.path.relpath(abs_p, project_root)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/stream")
def stream():
    def event_stream():
        q = announcer.listen()
        while True:
            msg = q.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

class CodeWatcher(FileSystemEventHandler):
    def __init__(self):
        self._timer = None

    @staticmethod
    def _is_relevant(path):
        if not path:
            return False
        norm = path.replace("\\", "/").lower()
        return norm.endswith(".py") and "/core_engine/" not in norm

    def on_any_event(self, event):
        if getattr(event, "is_directory", False):
            return
        if event.event_type not in {"modified", "created", "moved", "deleted"}:
            return

        src_path = getattr(event, "src_path", "")
        dest_path = getattr(event, "dest_path", "")
        if not (self._is_relevant(src_path) or self._is_relevant(dest_path)):
            return

        if self._timer:
            self._timer.cancel()

        def run_refresh():
            try:
                refresh_context(WATCH_PROJECT_ROOT, WATCH_OUTPUT_DIR)
                announcer.announce("reload")
            except Exception as exc:
                print(f"[Watcher] refresh failed: {exc}")

        self._timer = threading.Timer(1.0, run_refresh)
        self._timer.start()

def run_server(project_root, output_dir, host="0.0.0.0", port=5005, watch=True):
    global WATCH_PROJECT_ROOT, WATCH_OUTPUT_DIR
    WATCH_PROJECT_ROOT = os.path.abspath(project_root)
    WATCH_OUTPUT_DIR = os.path.abspath(output_dir)
    os.makedirs(WATCH_OUTPUT_DIR, exist_ok=True)

    observer = None
    if watch:
        observer = Observer()
        observer.schedule(CodeWatcher(), path=WATCH_PROJECT_ROOT, recursive=True)
        observer.start()
        atexit.register(lambda: (observer.stop(), observer.join(timeout=2)))

    url = f"http://localhost:{port}/dashboard"
    print(f"UTCAP Pilot server: {url}")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, threaded=True)

if __name__ == "__main__":
    run_server(os.getcwd(), "output")
