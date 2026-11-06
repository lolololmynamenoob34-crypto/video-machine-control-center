from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, subprocess, urllib.parse, os, re

ROOT = Path(__file__).resolve().parent
VIDEO_ROOT = Path(os.environ.get("VIDEO_MACHINE_ROOT", r"D:\VideoMachine")).resolve()
PYTHON = VIDEO_ROOT / ".venv" / "Scripts" / "python.exe"
FACTORY = VIDEO_ROOT / "factory.py"
HOST, PORT = "127.0.0.1", 8765
JOB_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")

def run_factory(args, timeout=1800):
    if not PYTHON.is_file(): return {"ok": False, "output": f"Project Python not found: {PYTHON}"}
    if not FACTORY.is_file(): return {"ok": False, "output": f"factory.py not found: {FACTORY}"}
    try:
        p = subprocess.run([str(PYTHON), str(FACTORY), *args], cwd=str(VIDEO_ROOT), capture_output=True, text=True, timeout=timeout, shell=False)
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return {"ok": p.returncode == 0, "returncode": p.returncode, "output": out[-18000:]}
    except subprocess.TimeoutExpired: return {"ok": False, "output": f"Command timed out after {timeout} seconds."}
    except Exception as e: return {"ok": False, "output": str(e)}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print("%s - %s" % (self.address_string(), fmt % args))
    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/status":
            result = run_factory(["status"], 45); result["video_root"] = str(VIDEO_ROOT); result["engine_paths_exist"] = PYTHON.is_file() and FACTORY.is_file(); return self.send_json(result)
        if path in ("/", "/index.html"):
            data = (ROOT / "web" / "index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); return self.wfile.write(data)
        return self.send_json({"ok": False, "error": "Not found"}, 404)
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 10000: return self.send_json({"ok": False, "output": "Request too large."}, 413)
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception: return self.send_json({"ok": False, "output": "Invalid JSON."}, 400)
        if path != "/api/action": return self.send_json({"ok": False, "error": "Not found"}, 404)
        action = data.get("action")
        commands = {"on": (["on"],45), "off": (["off"],45), "run-once": (["run-once"],1800), "watch": (["watch"],10), "schedule": (["schedule"],120), "status": (["status"],45)}
        if action in commands:
            args, timeout = commands[action]; return self.send_json(run_factory(args, timeout))
        if action not in ("import", "approve", "reject", "requeue", "published"): return self.send_json({"ok":False,"output":"Unsupported action."},400)
        job = str(data.get("job", "")).strip()
        if action != "import" and not JOB_RE.fullmatch(job): return self.send_json({"ok":False,"output":"Enter a valid job ID (letters, numbers, dot, underscore, hyphen)."},400)
        if action == "import":
            name = str(data.get("file", "")).strip(); candidate = (VIDEO_ROOT / name).resolve()
            if candidate.parent != VIDEO_ROOT or candidate.suffix.lower() != ".json" or not candidate.is_file(): return self.send_json({"ok":False,"output":"Choose an existing .json file directly inside D:\\VideoMachine, e.g. batch1.json."},400)
            return self.send_json(run_factory(["import", str(candidate)],120))
        if action == "approve":
            if not data.get("checked"): return self.send_json({"ok":False,"output":"Confirm you watched the video and checked its sources first."},400)
            return self.send_json(run_factory(["approve",job,"--checked"],120))
        if action == "reject":
            reason = str(data.get("reason", "")).strip()[:500]
            if not reason: return self.send_json({"ok":False,"output":"A rejection reason is required."},400)
            return self.send_json(run_factory(["reject",job,reason],120))
        if action == "requeue": return self.send_json(run_factory(["requeue",job],120))
        url = str(data.get("url", "")).strip()
        if not url.startswith(("https://www.youtube.com/", "https://youtu.be/")): return self.send_json({"ok":False,"output":"Enter a YouTube video URL."},400)
        return self.send_json(run_factory(["published",job,url],120))

if __name__ == "__main__":
    print(f"Video Machine Control Center: http://{HOST}:{PORT}")
    print(f"Factory root: {VIDEO_ROOT}")
    print("Local-only server. Keep this window open while using the dashboard.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
