@echo off
setlocal

set "CAMERA_INDEX=%~1"
if "%CAMERA_INDEX%"=="" set "CAMERA_INDEX=0"


set "PYTHONW_EXE=C:\Users\11blu\Documents\Perovskite-Automated-Synthesis-System-V2\Code\.venv\Scripts\pythonw.exe"
set "LAUNCHER_PY=C:\Users\11blu\Documents\Perovskite-Automated-Synthesis-System-V2\Code\src\gui_mock_launcher.py"

start "" "%PYTHONW_EXE%" "%LAUNCHER_PY%" --camera-index "%CAMERA_INDEX%"

endlocal