from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication

from sales_os.config import APP_NAME
from sales_os.engine import SalesEngine
from sales_os.scheduler import EngineScheduler
from sales_os.store import LOG_DIR, Store
from sales_os.ui import MainWindow


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_DIR / "sales_os.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[handler],
    )


def main() -> None:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    store = Store()
    engine = SalesEngine(store)
    scheduler = EngineScheduler(store, engine)
    scheduler.start()
    window = MainWindow(store, engine, scheduler, start_minimized="--minimized" in sys.argv)
    if "--minimized" not in sys.argv:
        window.show()
    from PySide6.QtCore import QTimer
    QTimer.singleShot(1500, scheduler.run_startup_cycle)
    code = app.exec()
    scheduler.stop()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
