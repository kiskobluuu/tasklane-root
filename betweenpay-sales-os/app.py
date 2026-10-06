import sys
from PySide6.QtWidgets import QApplication
from sales_os.store import Store
from sales_os.engine import SalesEngine
from sales_os.ui import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BetweenPay Sales OS")
    store = Store()
    engine = SalesEngine(store)
    window = MainWindow(store, engine)
    window.resize(1180, 760)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
