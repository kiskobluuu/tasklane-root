from __future__ import annotations

import os
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "BetweenPaySalesOS"


def command_for_startup() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    app_py = Path(__file__).resolve().parents[1] / "app.py"
    return f'"{sys.executable}" "{app_py}" --minimized'


def set_run_on_startup(enabled: bool) -> None:
    if os.name != "nt":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command_for_startup())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
