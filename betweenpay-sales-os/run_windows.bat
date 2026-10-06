@echo off
setlocal
cd /d %~dp0
where py >nul 2>&1
if errorlevel 1 (
  echo Python 3 is required. Install Python 3.12 or newer from python.org and try again.
  pause
  exit /b 1
)
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
