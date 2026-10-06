@echo off
cd /d %~dp0
call .venv\Scripts\activate
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name BetweenPaySalesOS app.py
echo.
echo Build complete. See dist\BetweenPaySalesOS\
pause
