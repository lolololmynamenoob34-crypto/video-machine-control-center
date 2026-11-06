#!/usr/bin/env python3
"""Local-only bridge for Video Machine Control Center.

Binds exclusively to 127.0.0.1. It deliberately refuses generation/rendering until
an explicit machine command is configured, so the UI cannot fake a successful run.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, subprocess, sys, webbrowser

ROOT = Path(os.environ.get("VIDEO_MACHINE_ROOT", r"D:\VideoMachine")).resolve()
OUTPUT = ROOT / "output"
HOST, PORT = "127.0.0.1", 8765
# Set these environment variables to the REAL, tested entry points only after checking
# the machine scripts. Do not put API keys in this file.
COMMANDS = {
    "generate": os.environ.get("VIDEO_MACHINE_GENERATE_COMMAND", ""),
    "render": os.environ.get("VIDEO_MACHINE_RENDER_COMMAND", ""),
}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(200, {"ok": True})

    def do_GET(self):
        if self.path != "/api/status":
            return self.send_json(404, {"ok": False, "error": "Unknown endpoint"})
        outputs = list(OUTPUT.glob("*")) if OUTPUT.exists() else []
        self.send_json(200, {
            "ok": True, "version": "Video Machine local bridge 0.1",
            "machineStatus": "Ready" if ROOT.exists() else "Machine folder not found",
            "outputCount": len(outputs),
            "rootExists": ROOT.exists(),
        })

    def do_POST(self):
        if self.path != "/api/task":
            return self.send_json(404, {"ok": False, "error": "Unknown endpoint"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16000:
                return self.send_json(413, {"ok": False, "error": "Request too large"})
            data = json.loads(self.rfile.read(length) or b"{}")
            task, brief = data.get("task"), str(data.get("brief", "")).strip()
            if task == "status":
                outputs = list(OUTPUT.glob("*")) if OUTPUT.exists() else []
                return self.send_json(200, {"ok": True, "message": f"Machine folder exists: {ROOT.exists()}; outputs: {len(outputs)}"})
            if task == "open_output":
                OUTPUT.mkdir(parents=True, exist_ok=True)
                os.startfile(str(OUTPUT)) if os.name == "nt" else webbrowser.open(OUTPUT.as_uri())
                return self.send_json(200, {"ok": True, "message": "Opened output folder"})
            if task not in ("generate", "render"):
                return self.send_json(400, {"ok": False, "error": "Unsupported task"})
            command = COMMANDS.get(task, "")
            if not command:
                return self.send_json(501, {"ok": False, "error": f"{task} is not connected yet. Configure VIDEO_MACHINE_{task.upper()}_COMMAND only after identifying the actual script entry point."})
            if not brief:
                return self.send_json(400, {"ok": False, "error": "A brief is required"})
            # Deliberately do not interpolate the brief into a shell command.
            args = [sys.executable, "-c", "import sys; print('Configured command must be implemented as a reviewed argument list, not shell text.')"]
            return self.send_json(501, {"ok": False, "error": "Command adapter is intentionally not enabled. The machine entry point must be inspected before connecting execution."})
        except Exception as exc:
            return self.send_json(500, {"ok": False, "error": str(exc)})

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    if not ROOT.exists():
        print(f"WARNING: machine folder not found: {ROOT}")
    print(f"Video Machine bridge listening only on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
