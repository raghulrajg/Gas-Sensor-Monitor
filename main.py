"""
main.py
-------
Entry point for the Gas Sensor Monitor application.

Run with:
    python main.py
"""

import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gas Sensor Monitor")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
