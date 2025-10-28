@echo off
setlocal
REM ================================
REM ClaimAutomationDragDrop (CPU-only) setup
REM Creates .venv, installs deps (CPU), and launches the app
REM ================================

REM 1) Move to script directory
cd /d "%~dp0"

REM 2) Create venv (Python 3.12)
py -3.12 -m venv .venv
if errorlevel 1 (
  echo [X] Failed to create venv. Ensure Python 3.12 is installed and on PATH.
  pause
  exit /b 1
)

REM 3) Activate venv
call .\.venv\Scripts\activate

REM 4) Upgrade pip/setuptools/wheel
python -m pip install --upgrade pip setuptools wheel

REM 5) Install CPU-only requirements
pip install -r requirements-cpu.txt
if errorlevel 1 (
  echo [X] Dependency install failed. Check internet connection and try again.
  pause
  exit /b 1
)

REM 6) Sanity print
python - <<PY
import torch, easyocr
print("Torch:", torch.__version__, "| CUDA available:", torch.cuda.is_available())
print("EasyOCR import OK")
PY

REM 7) Run the app
python main.py
endlocal
