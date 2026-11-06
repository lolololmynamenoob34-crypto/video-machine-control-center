# Video Machine Control Center

A local-first dashboard for controlling the existing factory.py video engine. It does not replace the engine or pretend that a job succeeded when the CLI reports failure.

## Features

- **Overview:** engine connectivity, real CLI status output, file inventory, and factory controls.
- **Script Queue:** discover JSON batch files and import a batch into the factory.
- **Video Review:** discover rendered videos; approve, reject, or requeue jobs by their exact factory job ID.
- **Publishing Schedule:** run the factory schedule command and list schedule-like files discovered on disk.
- **Settings & Diagnostics:** display the active factory root, Python executable, path checks, local bind address, and publishing safety state.
- **Watch mode:** start a background factory.py watch process and stop it from the dashboard without a short HTTP timeout killing it.

## Safety

- Binds to 127.0.0.1 only; not exposed to other devices on the network.
- Uses an allowlist of documented factory commands and no shell command execution.
- Does not upload or publish videos.
- Approval requires explicit confirmation that the full video and its sources were checked.
- File inventory is a discovery aid, not a claim that a job is queued, approved, or scheduled. The factory CLI remains the source of truth for job state.
- Uses Python's standard library; no extra dashboard pip packages are required.

## Run on Windows

1. Keep this dashboard folder separate from the engine folder.
2. Ensure the engine folder contains factory.py and .venv\Scripts\python.exe.
3. Double-click start-dashboard.bat. It first checks %USERPROFILE%\Downloads\videomachine_v2, then D:\VideoMachine; if neither matches, it asks for the folder containing factory.py.
4. Open http://127.0.0.1:8765.
5. Keep the black server window open while using the dashboard.

If your engine uses a different path, set VIDEO_MACHINE_ROOT in the launcher or enter the correct path when prompted.

## Important limitations

This dashboard invokes the engine's existing CLI. It cannot guarantee every engine action works until tested against the exact local factory.py and real data. If the engine CLI reports an error, that error is displayed. The inventory scans a limited set of file types and directory depth; it does not parse private job databases or infer job state from filenames. You must review the output, generated video, sources, and schedule yourself. YouTube publishing remains manual.
