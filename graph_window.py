"""
graph_window.py
----------------
Standalone top-level window used to view a single channel's graph large
(optionally full screen), separate from the main grid.

The window does NOT create a second copy of the plot - the caller's
existing pyqtgraph PlotWidget is reparented into this window so the graph
keeps updating live and stays perfectly in sync with the data feed. When
the window is closed, `closed` fires so the caller can reparent the plot
widget back into its original card.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton


class GraphPopoutWindow(QDialog):
    closed = Signal()

    def __init__(self, title: str, plot_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        # A real top-level window (not a modal popup) with its own
        # minimize/maximize/close controls, so it behaves like an
        # "open in external window" action rather than a dialog box.
        self.setWindowFlags(Qt.Window)
        self.resize(1000, 650)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        header = QHBoxLayout()
        header.addWidget(QLabel(f"<b>{title}</b>"))
        header.addStretch()

        self.fullscreen_btn = QPushButton("Full Screen")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        header.addWidget(self.fullscreen_btn)

        dock_btn = QPushButton("Dock Back")
        dock_btn.setToolTip("Close this window and return the graph to the main grid")
        dock_btn.clicked.connect(self.close)
        header.addWidget(dock_btn)

        layout.addLayout(header)
        layout.addWidget(plot_widget)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("Full Screen")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("Exit Full Screen")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self._toggle_fullscreen()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
