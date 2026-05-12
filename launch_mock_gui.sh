#!/usr/bin/env bash
set -euo pipefail

CAMERA_INDEX="${1:-0}"

REPO_SRC_DIR="/c/Users/11blu/Documents/Perovskite-Automated-Synthesis-System-V2/Code/src"
PYTHONW_WIN="C:\Users\11blu\Documents\Perovskite-Automated-Synthesis-System-V2\Code\.venv\Scripts\pythonw.exe"
LAUNCHER_WIN="C:\Users\11blu\Documents\Perovskite-Automated-Synthesis-System-V2\Code\src\gui_mock_launcher.py"

cd "$REPO_SRC_DIR"

# Use pythonw.exe so the GUI opens like a desktop app without keeping a console attached.
cmd.exe //c start "" "$PYTHONW_WIN" "$LAUNCHER_WIN" --camera-index "$CAMERA_INDEX"