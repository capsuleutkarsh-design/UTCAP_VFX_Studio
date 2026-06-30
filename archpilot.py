import os
import sys
from flask import Flask, jsonify, send_file, request, Response

app = Flask(__name__)

# Global configuration
WATCH_OUTPUT_DIR = None
client = None


def _build_context():
    """Build and save the project context."""
    global WATCH_OUTPUT_DIR
    
    if not WATCH_OUTPUT_DIR:
        WATCH_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.archpilot')
    
    context = {
        "project_root": os.getcwd(),
        "timestamp": str(datetime.datetime.now()),
        "python_files": [],
        "dependencies": 0,
        "npm_dependencies": []
    }
    
    # Find Python files
    for root, dirs, files in os.walk(os.getcwd()):
        # Skip hidden directories and venv
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'venv']
        
        for file in files:
            if file.endswith('.py'):
                context["python_files"].append(os.path.join(root, file))
    
    # Count dependencies (simplified)
    try:
        with open('requirements.txt', 'r') as f:
            context["dependencies"] = len([line for line in f.readlines() if line.strip()])
    except FileNotFoundError:
        pass
    
    # Save context
    os.makedirs(WATCH_OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(WATCH_OUTPUT_DIR, 'context.json'), 'w', encoding='utf-8') as f:
        json.dump(context, f, indent=2)
    
    return context


@app.route('/')
def index():
    """Serve the main dashboard."""
    # Simple inline HTML
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>UTCAP AI Pilot</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 2rem; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #333; margin-top: 0; }
            .status { padding: 1rem; background: #e8f5e9; border-left: 4px solid #4caf50; margin-bottom: 1rem; }
            button { background: #2196f3; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 4px; cursor: pointer; font-size: 1rem; margin-right: 0.5rem; }
            button:hover { background: #1976d2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>UTCAP AI Pilot</h1>
            <p>Welcome to the Architectural Intelligence Server!</p>
            
            <div class="status">
                <h3>Status: Ready</h3>
                <ul>
                    <li>Gemini API: """ + ("Connected" if client else "Not Configured") + """</li>
                    <li>Python Files Found: """ + str(len(_build_context().get('python_files', []))) + """</li>
                </ul>
            </div>
            
            <h3>Quick Actions:</h3>
            <button onclick="location.reload()">Reload Context</button>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/api/context')
def api_context():
    """Return current context."""
    context = _build_context()
    return jsonify(context)


if __name__ == '__main__':
    import json
    import datetime
    
    # Override the global WATCH_OUTPUT_DIR
    WATCH_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.archpilot')
    
    print("UTCAP AI Pilot starting...")
    
    # Initialize Gemini client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("   [!] GEMINI_API_KEY not set. AI features will be disabled.")
    else:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel('gemini-pro')
            print("   [✓] Gemini API initialized successfully")
        except ImportError:
            print("   [!] google-generativeai package not installed. Run: pip install google-generativeai")
        except Exception as e:
            print(f"   [!] Failed to initialize Gemini: {e}")
    
    # Build initial context
    print("Building project context...")
    _build_context()
    
    print(f"Server running on http://localhost:5000")
    app.run(debug=True, port=5000)