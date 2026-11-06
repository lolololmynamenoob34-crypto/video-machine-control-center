from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, subprocess, urllib.parse, os, re, threading, time

ROOT = Path(__file__).resolve().parent
VIDEO_ROOT = Path(os.environ.get("VIDEO_MACHINE_ROOT", r"D:\VideoMachine")).resolve()
PYTHON = VIDEO_ROOT / ".venv" / "Scripts" / "python.exe"
FACTORY = VIDEO_ROOT / "factory.py"
HOST, PORT = "127.0.0.1", 8765
JOB_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")
WATCH_LOCK = threading.Lock()
WATCH_PROCESS = None
WATCH_STARTED_AT = None
SCAN_DIRS = ("", "queue", "queues", "jobs", "output", "outputs", "rendered", "renders", "videos", "review", "reviews", "published", "schedule", "schedules", "logs", "data")
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "site-packages"}

def run_factory(args, timeout=1800):
    if not PYTHON.is_file():
        return {"ok": False, "output": f"Project Python not found: {PYTHON}"}
    if not FACTORY.is_file():
        return {"ok": False, "output": f"factory.py not found: {FACTORY}"}
    try:
        p = subprocess.run([str(PYTHON), str(FACTORY), *[str(x) for x in args]], cwd=str(VIDEO_ROOT),
                           capture_output=True, text=True, timeout=timeout, shell=False)
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return {"ok": p.returncode == 0, "returncode": p.returncode, "output": out[-18000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": f"Command timed out after {timeout} seconds. The process was stopped by the server."}
    except Exception as e:
        return {"ok": False, "output": str(e)}

def watch_status():
    global WATCH_PROCESS, WATCH_STARTED_AT
    with WATCH_LOCK:
        if WATCH_PROCESS is not None and WATCH_PROCESS.poll() is not None:
            WATCH_PROCESS = None
            WATCH_STARTED_AT = None
        running = WATCH_PROCESS is not None and WATCH_PROCESS.poll() is None
        return {"running": running, "pid": WATCH_PROCESS.pid if running else None,
                "started_at": WATCH_STARTED_AT if running else None}

def start_watch():
    global WATCH_PROCESS, WATCH_STARTED_AT
    with WATCH_LOCK:
        if WATCH_PROCESS is not None and WATCH_PROCESS.poll() is None:
            return {"ok": True, "output": f"Watch mode is already running (PID {WATCH_PROCESS.pid}).", "watch": watch_status_unlocked()}
        if not PYTHON.is_file() or not FACTORY.is_file():
            return {"ok": False, "output": f"Factory or project Python missing. Expected {PYTHON} and {FACTORY}."}
        try:
            log_path = ROOT / "watch-mode.log"
            log_file = open(log_path, "a", encoding="utf-8")
            WATCH_PROCESS = subprocess.Popen([str(PYTHON), str(FACTORY), "watch"], cwd=str(VIDEO_ROOT),
                stdout=log_file, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            log_file.close()
            WATCH_STARTED_AT = time.time()
            return {"ok": True, "output": f"Watch mode started in background (PID {WATCH_PROCESS.pid}). Output: {log_path}", "watch": watch_status_unlocked()}
        except Exception as e:
            return {"ok": False, "output": f"Could not start watch mode: {e}"}

def watch_status_unlocked():
    running = WATCH_PROCESS is not None and WATCH_PROCESS.poll() is None
    return {"running": running, "pid": WATCH_PROCESS.pid if running else None,
            "started_at": WATCH_STARTED_AT if running else None}

def stop_watch():
    global WATCH_PROCESS, WATCH_STARTED_AT
    with WATCH_LOCK:
        proc = WATCH_PROCESS
        if proc is None or proc.poll() is not None:
            WATCH_PROCESS = None
            WATCH_STARTED_AT = None
            return {"ok": True, "output": "Watch mode is not running."}
        try:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            pid = proc.pid
            WATCH_PROCESS = None
            WATCH_STARTED_AT = None
            return {"ok": True, "output": f"Watch mode stopped (PID {pid})."}
        except Exception as e:
            return {"ok": False, "output": f"Could not stop watch mode: {e}"}

def safe_inventory():
    items = []
    seen = set()
    roots = [VIDEO_ROOT / name for name in SCAN_DIRS]
    for base in roots:
        if not base.exists() or not base.is_dir():
            continue
        try:
            for current, dirs, files in os.walk(base):
                cur = Path(current)
                try:
                    depth = len(cur.relative_to(VIDEO_ROOT).parts)
                except ValueError:
                    dirs[:] = []
                    continue
                dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and depth < 4]
                for name in files:
                    p = cur / name
                    ext = p.suffix.lower()
                    if ext not in (".mp4", ".mov", ".webm", ".mkv", ".json", ".csv", ".txt", ".log", ".srt", ".vtt"):
                        continue
                    try:
                        resolved = p.resolve()
                        if not resolved.is_relative_to(VIDEO_ROOT) or resolved in seen:
                            continue
                        seen.add(resolved)
                        stat = resolved.stat()
                        if stat.st_size > 2_000_000_000:
                            continue
                        rel = str(resolved.relative_to(VIDEO_ROOT))
                        category = ("video" if ext in (".mp4", ".mov", ".webm", ".mkv") else
                                    "script/batch" if ext == ".json" else
                                    "schedule" if "schedul" in rel.lower() or ext == ".csv" else
                                    "subtitle" if ext in (".srt", ".vtt") else "log/data")
                        items.append({"name": name, "path": rel, "type": category, "extension": ext,
                                      "size_bytes": stat.st_size, "modified": stat.st_mtime})
                    except (OSError, ValueError):
                        continue
        except OSError:
            continue
    items.sort(key=lambda x: x["modified"], reverse=True)
    return items[:500]

def status_payload():
    result = run_factory(["status"], 45)
    result["video_root"] = str(VIDEO_ROOT)
    result["python_path"] = str(PYTHON)
    result["factory_path"] = str(FACTORY)
    result["engine_paths_exist"] = PYTHON.is_file() and FACTORY.is_file()
    result["watch"] = watch_status()
    return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/status":
            return self.send_json(status_payload())
        if path == "/api/data":
            items = safe_inventory()
            return self.send_json({"ok": True, "items": items, "counts": {
                "videos": sum(x["type"] == "video" for x in items),
                "batches": sum(x["type"] == "script/batch" for x in items),
                "schedules": sum(x["type"] == "schedule" for x in items),
                "other": sum(x["type"] not in ("video", "script/batch", "schedule") for x in items)},
                "watch": watch_status()})
        if path == "/api/settings":
            return self.send_json({"ok": True, "settings": {
                "dashboard_url": f"http://{HOST}:{PORT}", "bind_address": HOST,
                "port": PORT, "video_root": str(VIDEO_ROOT), "python": str(PYTHON),
                "factory": str(FACTORY), "python_exists": PYTHON.is_file(),
                "factory_exists": FACTORY.is_file(), "auto_publish": False,
                "watch": watch_status(), "scan_limit": 500}})
        if path in ("/", "/index.html"):
            try:
                data = (ROOT / "web" / "index.html").read_bytes()
            except OSError as e:
                return self.send_json({"ok": False, "error": str(e)}, 500)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return self.wfile.write(data)
        return self.send_json({"ok": False, "error": "Not found"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 10000:
                return self.send_json({"ok": False, "output": "Request too large."}, 413)
            data = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object.")
        except Exception:
            return self.send_json({"ok": False, "output": "Invalid JSON object."}, 400)
        if path == "/api/watch":
            action = data.get("action")
            if action == "start":
                return self.send_json(start_watch())
            if action == "stop":
                return self.send_json(stop_watch())
            return self.send_json({"ok": False, "output": "Use action start or stop."}, 400)
        if path != "/api/action":
            return self.send_json({"ok": False, "error": "Not found"}, 404)
        action = data.get("action")
        if action == "watch":
            return self.send_json(start_watch())
        if action == "off":
            stopped = stop_watch()
            result = run_factory(["off"], 45)
            result["output"] = (stopped.get("output", "") + "\n" + result.get("output", "")).strip()
            return self.send_json(result)
        commands = {"on": (["on"], 45), "run-once": (["run-once"], 1800),
                    "schedule": (["schedule"], 120), "status": (["status"], 45)}
        if action in commands:
            args, timeout = commands[action]
            result = run_factory(args, timeout)
            if action in ("run-once", "schedule", "on", "status"):
                result["inventory"] = safe_inventory()
            return self.send_json(result)
        if action not in ("import", "approve", "reject", "requeue", "published"):
            return self.send_json({"ok": False, "output": "Unsupported action."}, 400)
        job = str(data.get("job", "")).strip()
        if action != "import" and not JOB_RE.fullmatch(job):
            return self.send_json({"ok": False, "output": "Enter a valid job ID (letters, numbers, dot, underscore, hyphen)."}, 400)
        if action == "import":
            name = str(data.get("file", "")).strip()
            candidate = (VIDEO_ROOT / name).resolve()
            if candidate.parent != VIDEO_ROOT or candidate.suffix.lower() != ".json" or not candidate.is_file():
                return self.send_json({"ok": False, "output": f"Choose an existing .json file directly inside {VIDEO_ROOT}, e.g. batch1.json."}, 400)
            return self.send_json(run_factory(["import", str(candidate)], 120))
        if action == "approve":
            if not data.get("checked"):
                return self.send_json({"ok": False, "output": "Confirm you watched the video and checked its sources first."}, 400)
            return self.send_json(run_factory(["approve", job, "--checked"], 120))
        if action == "reject":
            reason = str(data.get("reason", "")).strip()[:500]
            if not reason:
                return self.send_json({"ok": False, "output": "A rejection reason is required."}, 400)
            return self.send_json(run_factory(["reject", job, reason], 120))
        if action == "requeue":
            return self.send_json(run_factory(["requeue", job], 120))
        url = str(data.get("url", "")).strip()
        if not re.fullmatch(r"https://(?:www\.)?(?:youtube\.com/watch\?[^\s]+|youtu\.be/[A-Za-z0-9_-]+)(?:[^\s]*)", url):
            return self.send_json({"ok": False, "output": "Enter a valid https YouTube watch or youtu.be URL."}, 400)
        return self.send_json(run_factory(["published", job, url], 120))

if __name__ == "__main__":
    print(f"Video Machine Control Center: http://{HOST}:{PORT}")
    print(f"Factory root: {VIDEO_ROOT}")
    print("Local-only server. Keep this window open while using the dashboard.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
