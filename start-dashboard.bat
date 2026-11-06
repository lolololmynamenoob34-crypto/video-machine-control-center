@echo off
setlocal
set "VIDEO_MACHINE_ROOT=D:\VideoMachine"
cd /d "%~dp0"
if not exist "%VIDEO_MACHINE_ROOT%\factory.py" (
  echo ERROR: Cannot find D:\VideoMachine\factory.py
  echo Edit start-dashboard.bat to match your actual factory folder.
  pause
  exit /b 1
)
"%VIDEO_MACHINE_ROOT%\.venv\Scripts\python.exe" "%~dp0server.py"
pause
