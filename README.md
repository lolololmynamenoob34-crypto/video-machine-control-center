# Video Machine Control Center

Local-first web dashboard for controlling the existing `D:\VideoMachine` Python factory.

## Safety
- Binds to `127.0.0.1` only; not exposed to your network.
- Calls only an allowlist of `factory.py` commands.
- Does not upload or publish videos.
- Approval requires confirmation that you watched the video and checked sources.
- Uses Python's standard library; no extra pip packages required.

## Run
1. Put this folder at `D:\VideoMachine\control-center`.
2. Ensure the existing factory is `D:\VideoMachine\factory.py` and Python is `D:\VideoMachine\.venv\Scripts\python.exe`.
3. Double-click `start-dashboard.bat`.
4. Open `http://127.0.0.1:8765`.

The dashboard invokes the CLI commands from your instructions. If the real factory differs, it displays the actual error instead of pretending it worked.
