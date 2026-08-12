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

    # Force the Fusion style: the native platform styles (windowsvista,
    # macOS, etc.) largely IGNORE custom QSS colors on standard controls
    # (buttons, combo boxes, menus, sliders...), so only plain widget
    # backgrounds would change and the Light/Dark theme switch looked
    # broken. Fusion fully respects stylesheets/palette on every widget.
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
