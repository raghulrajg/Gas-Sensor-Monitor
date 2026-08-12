"""
main_window.py
---------------
Top level application window: menu bar (File / View), connection bar,
9-channel grid (7 gas sensors + temperature + humidity), recording
controls, and settings import/export.
"""

import time
import datetime as _dt

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QLabel,
    QMessageBox,
    QFileDialog,
    QScrollArea,
    QStatusBar,
)

import config
from sensor_widget import SensorWidget
from serial_worker import SerialWorker, list_available_ports
from data_recorder import DataRecorder, export_settings_only, import_settings
from dialogs import LineColorDialog, ThemeDialog, LayoutDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gas Sensor Monitor")
        self.resize(1400, 850)

        self.worker = None          # SerialWorker instance while connected
        self.recorder = DataRecorder()
        self.connected = False
        self.last_values = [float("nan")] * config.NUM_CHANNELS
        self._session_start = None  # wall-clock reference for the time (x) axis

        self.line_colors = {ch["key"]: ch["color"] for ch in config.CHANNELS}
        self.theme = dict(config.THEME_PRESETS[config.DEFAULT_THEME])
        self.layout_order = [ch["key"] for ch in config.CHANNELS]
        self.layout_columns = config.DEFAULT_GRID_COLUMNS

        self._build_menu_bar()
        self._build_ui()
        self._refresh_ports()
        self._apply_theme(self.theme["background"], self.theme["text"], self.theme["card"])

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed_label)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------
    def _build_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        import_action = QAction("Import Settings...", self)
        import_action.triggered.connect(self._on_import_settings_clicked)
        file_menu.addAction(import_action)

        export_action = QAction("Export Current Settings...", self)
        export_action.triggered.connect(self._on_export_settings_clicked)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("&View")

        colors_action = QAction("Line Colors...", self)
        colors_action.triggered.connect(self._on_line_colors_clicked)
        view_menu.addAction(colors_action)

        theme_action = QAction("Application Theme...", self)
        theme_action.triggered.connect(self._on_theme_clicked)
        view_menu.addAction(theme_action)

        layout_action = QAction("Graph Layout...", self)
        layout_action.triggered.connect(self._on_layout_clicked)
        view_menu.addAction(layout_action)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addLayout(self._build_connection_bar())
        root.addLayout(self._build_record_bar())

        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        root.addWidget(self.grid_scroll)

        self._create_sensor_widgets()
        self._rebuild_grid()

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Not connected")

    def _build_connection_bar(self):
        row = QHBoxLayout()

        row.addWidget(QLabel("COM Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(260)
        row.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        row.addWidget(self.refresh_btn)

        row.addWidget(QLabel(f"Baud Rate: {config.BAUDRATE}"))

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        row.addWidget(self.connect_btn)

        row.addStretch()
        return row

    def _build_record_bar(self):
        row = QHBoxLayout()

        self.record_btn = QPushButton("\u25cf Record")
        self.record_btn.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.record_btn.clicked.connect(self._on_record_clicked)
        row.addWidget(self.record_btn)

        self.stop_btn = QPushButton("\u25a0 Stop && Export")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        row.addWidget(self.stop_btn)

        self.clear_btn = QPushButton("Clear Graphs")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        row.addWidget(self.clear_btn)

        self.record_status_label = QLabel("Not recording")
        row.addWidget(self.record_status_label)

        row.addStretch()
        return row

    def _create_sensor_widgets(self):
        self.sensor_widgets = {}
        for ch in config.CHANNELS:
            sw = SensorWidget(
                key=ch["key"],
                name=ch["name"],
                unit=ch["unit"],
                calibration=ch["calibration"],
                gas_index=ch["gas_index"],
                color=self.line_colors[ch["key"]],
            )
            if ch["calibration"]:
                sw.calibration_changed.connect(self._on_calibration_changed)
            self.sensor_widgets[ch["key"]] = sw

    def _rebuild_grid(self):
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(10)
        cols = max(1, self.layout_columns)
        for i, key in enumerate(self.layout_order):
            grid.addWidget(self.sensor_widgets[key], i // cols, i % cols)
        self.grid_scroll.setWidget(container)

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------
    def _refresh_ports(self):
        self.port_combo.clear()
        ports = list_available_ports()
        if not ports:
            self.port_combo.addItem("No ports found")
        else:
            for device, desc in ports:
                self.port_combo.addItem(f"{device} - {desc}", userData=device)

    def _on_connect_clicked(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        device = self.port_combo.currentData()
        if not device:
            QMessageBox.warning(self, "No Port Selected", "Please select a valid COM port.")
            return

        self.worker = SerialWorker(device, config.BAUDRATE)
        self.worker.data_received.connect(self._on_data_received)
        self.worker.status_changed.connect(self.statusBar().showMessage)
        self.worker.settings_line_received.connect(self._on_settings_line_received)
        self.worker.start()

        self.connected = True
        self._session_start = time.time()
        self.connect_btn.setText("Disconnect")
        self._set_connection_controls_enabled(False)

    def _disconnect(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker = None

        self.connected = False
        self.connect_btn.setText("Connect")
        self._set_connection_controls_enabled(True)
        self.statusBar().showMessage("Disconnected")

    def _set_connection_controls_enabled(self, enabled: bool):
        self.port_combo.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Live data + calibration
    # ------------------------------------------------------------------
    def _on_data_received(self, values):
        self.last_values = values
        if self._session_start is None:
            self._session_start = time.time()
        elapsed = time.time() - self._session_start

        for ch, v in zip(config.CHANNELS, values):
            self.sensor_widgets[ch["key"]].add_sample(elapsed, v)

        if self.recorder.is_recording:
            self.recorder.write_sample(values)
            self.record_status_label.setText(
                f"Recording... {self.recorder.sample_count} samples"
            )

    def _on_calibration_changed(self, gas_index: int, value: float):
        if self.worker is None:
            self.statusBar().showMessage("Failed to send calibration (not connected)", 3000)
            return
        ok = self.worker.send_calibration(gas_index, value)
        name = next(c["name"] for c in config.CHANNELS if c.get("gas_index") == gas_index)
        msg = f"Sent calibration for {name}: {value:.2f}" if ok else "Failed to send calibration"
        self.statusBar().showMessage(msg, 3000)

    def _on_settings_line_received(self, gas_index: int, value: float):
        for ch in config.CHANNELS:
            if ch.get("gas_index") == gas_index:
                self.sensor_widgets[ch["key"]].set_calibration_silent(value)
                break

    def _on_clear_clicked(self):
        for sw in self.sensor_widgets.values():
            sw.clear_plot()
        self._session_start = time.time()
        self.statusBar().showMessage("Graphs cleared", 2000)

    # ------------------------------------------------------------------
    # Recording / export
    # ------------------------------------------------------------------
    def _on_record_clicked(self):
        if not self.connected:
            QMessageBox.warning(self, "Not Connected", "Connect to a device before recording.")
            return
        if self.recorder.is_recording:
            return
        self.recorder.start()
        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.record_status_label.setText("Recording... 0 samples")
        self._elapsed_timer.start(1000)

    def _on_stop_clicked(self):
        if not self.recorder.is_recording:
            return
        self._elapsed_timer.stop()

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Recorded Data",
            f"gas_data_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)",
        )

        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if not filepath:
            reply = QMessageBox.question(
                self,
                "Discard Recording?",
                "No file was chosen. Discard the recorded data?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.recorder.discard()
                self.record_status_label.setText("Not recording")
            else:
                self.stop_btn.setEnabled(True)
                self._elapsed_timer.start(1000)
            return

        calibration_values = self._current_calibration_values()
        port_info = self._current_port_info()
        saved_path, count = self.recorder.stop_and_save(filepath, calibration_values, port_info)
        self.record_status_label.setText(f"Saved {count} samples to {saved_path}")
        QMessageBox.information(self, "Export Complete", f"Saved {count} samples to:\n{saved_path}")

    def _update_elapsed_label(self):
        if self.recorder.is_recording:
            elapsed = (_dt.datetime.now() - self.recorder.start_time).total_seconds()
            self.record_status_label.setText(
                f"Recording... {self.recorder.sample_count} samples ({int(elapsed)}s)"
            )

    def _current_calibration_values(self):
        gas_channels = [c for c in config.CHANNELS if c["calibration"]]
        return [self.sensor_widgets[c["key"]].current_calibration() for c in gas_channels]

    def _on_export_settings_clicked(self):
        calibration_values = self._current_calibration_values()
        port_info = self._current_port_info()
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Current Settings",
            f"gas_sensor_settings_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not filepath:
            return
        saved = export_settings_only(filepath, calibration_values, port_info)
        self.statusBar().showMessage(f"Settings exported to {saved}", 4000)

    def _on_import_settings_clicked(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Settings", "", "Excel Files (*.xlsx)"
        )
        if not filepath:
            return
        try:
            values_by_name = import_settings(filepath)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Import Failed", str(exc))
            return

        applied = 0
        for ch in config.CHANNELS:
            if not ch["calibration"]:
                continue
            if ch["name"] in values_by_name:
                value = values_by_name[ch["name"]]
                sw = self.sensor_widgets[ch["key"]]
                sw.set_calibration_silent(value)
                applied += 1
                if self.worker is not None:
                    self.worker.send_calibration(ch["gas_index"], value)

        msg = f"Imported calibration for {applied} sensor(s) from {filepath}"
        if self.worker is not None:
            msg += " and sent to device"
        self.statusBar().showMessage(msg, 5000)
        QMessageBox.information(self, "Import Complete", msg)

    def _current_port_info(self):
        return {
            "port": self.port_combo.currentData() or "",
            "baudrate": config.BAUDRATE,
        }

    # ------------------------------------------------------------------
    # View menu actions: colors / theme / layout
    # ------------------------------------------------------------------
    def _on_line_colors_clicked(self):
        dlg = LineColorDialog(self.line_colors, self._apply_line_color, self)
        dlg.exec()

    def _apply_line_color(self, key: str, color: str):
        self.line_colors[key] = color
        self.sensor_widgets[key].set_line_color(color)

    def _on_theme_clicked(self):
        dlg = ThemeDialog(self.theme, self._apply_theme, self)
        dlg.exec()

    def _apply_theme(self, background: str, text: str, card: str):
        self.theme = {"background": background, "text": text, "card": card}
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background-color: {background}; color: {text}; }}
            QFrame#sensorCard {{ background-color: {card}; border-radius: 6px; border: 1px solid rgba(0,0,0,0.15); }}
            QScrollArea {{ background-color: {background}; border: none; }}
            """
        )

    def _on_layout_clicked(self):
        dlg = LayoutDialog(self.layout_order, self.layout_columns, self._apply_layout, self)
        dlg.exec()

    def _apply_layout(self, ordered_keys: list, columns: int):
        self.layout_order = ordered_keys
        self.layout_columns = columns
        self._rebuild_grid()

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if self.recorder.is_recording:
            reply = QMessageBox.question(
                self,
                "Recording in Progress",
                "A recording is in progress and has not been exported. Quit anyway and lose it?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        self._disconnect()
        event.accept()
