"""
HF Spaces entry point — runs a minimal HTTP server that:
1. Keeps the container alive (required by HF Spaces)
2. Runs inference on GET /run and streams the output
3. Returns health check on GET /
"""

import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import StringIO
from pathlib import Path

# Make email_triage importable
sys.path.insert(0, str(Path(__file__).parent / "email-triage-env"))

import inference


def run_all_tasks() -> str:
    """Run inference on all tasks and capture output."""
    old_stdout = sys.stdout
    sys.stdout = buffer = StringIO()

    try:
        for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
            agent = inference.HybridAgent()
            inference.run_task(task_id=task_id, agent=agent, episodes=200)
    finally:
        sys.stdout = old_stdout

    return buffer.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default access logs

    def do_GET(self):
        if self.path == "/":
            body = b"Email Triage Env - Running. GET /run to execute inference."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/run":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            output = run_all_tasks()
            self.wfile.write(output.encode())

        else:
            self.send_response(404)
            self.end_headers()


def run_inference_background():
    """Run inference once at startup and print to container logs."""
    print("===== Application Startup at", __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "=====", flush=True)
    for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
        agent = inference.HybridAgent()
        inference.run_task(task_id=task_id, agent=agent, episodes=200)


if __name__ == "__main__":
    # Run inference in background thread so server starts immediately
    t = threading.Thread(target=run_inference_background, daemon=True)
    t.start()

    # Keep container alive with HTTP server on port 7860
    port = int(os.getenv("PORT", 7860))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Server running on port {port}", flush=True)
    server.serve_forever()
