@echo off
setlocal
cd /d %~dp0
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest -q
if errorlevel 1 (
  echo Tests failed. Build stopped.
  pause
  exit /b 1
)
pyinstaller --noconfirm --clean --onefile --windowed --name BetweenPaySalesOS --collect-all keyring app.py
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo.
echo Build complete: dist\BetweenPaySalesOS.exe
pause
