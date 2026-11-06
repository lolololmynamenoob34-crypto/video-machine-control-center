@echo off
setlocal
rem Default to the current setup; change this if your factory lives elsewhere.
if not defined VIDEO_MACHINE_ROOT set "VIDEO_MACHINE_ROOT=%USERPROFILE%\Downloads\videomachine_v2"
if not exist "%VIDEO_MACHINE_ROOT%\factory.py" if exist "D:\VideoMachine\factory.py" set "VIDEO_MACHINE_ROOT=D:\VideoMachine"
if not exist "%VIDEO_MACHINE_ROOT%\factory.py" (
  echo Could not find factory.py in:
  echo   %VIDEO_MACHINE_ROOT%
  echo.
  set /p "VIDEO_MACHINE_ROOT=Paste the full folder path containing factory.py: "
)
if not exist "%VIDEO_MACHINE_ROOT%\factory.py" (
  echo ERROR: factory.py not found. No changes were made.
  pause
  exit /b 1
)
if not exist "%VIDEO_MACHINE_ROOT%\.venv\Scripts\python.exe" (
  echo ERROR: Project Python not found:
  echo   %VIDEO_MACHINE_ROOT%\.venv\Scripts\python.exe
  echo.
  echo Install Python dependencies for the factory first.
  pause
  exit /b 1
)
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"
"%VIDEO_MACHINE_ROOT%\.venv\Scripts\python.exe" -c "import ast,pathlib; ast.parse(pathlib.Path(r'%~dp0server.py').read_text(encoding='utf-8')); print('Server syntax check passed.')"
if errorlevel 1 (
  echo ERROR: server.py has a syntax error.
  pause
  exit /b 1
)
echo.
echo Factory root: %VIDEO_MACHINE_ROOT%
echo Dashboard: http://127.0.0.1:8765
echo Keep this window open. Press Ctrl+C to stop the dashboard server.
echo.
"%VIDEO_MACHINE_ROOT%\.venv\Scripts\python.exe" "%~dp0server.py"
pause
