"""
main_window.py
---------------
Top level application window: connection bar, 7-sensor grid, recording
controls and settings export.
"""

import datetime as _dt

from PySide6.QtCore import Qt, QTimer
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
    QCheckBox,
    QScrollArea,
    QStatusBar,
)

import config
from sensor_widget import SensorWidget
from serial_worker import SerialWorker, list_available_ports
from simulator import SimulatedSource
from data_recorder import DataRecorder, export_settings_only


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gas Sensor Monitor")
        self.resize(1400, 850)

        self.worker = None          # SerialWorker instance while connected
        self.simulator = None       # SimulatedSource instance while simulating
        self.recorder = DataRecorder()
        self.connected = False
        self.last_values = [float("nan")] * config.NUM_SENSORS

        self._build_ui()
        self._refresh_ports()

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed_label)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addLayout(self._build_connection_bar())
        root.addLayout(self._build_record_bar())
        root.addWidget(self._build_sensor_grid())

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Not connected")

    def _build_connection_bar(self):
        row = QHBoxLayout()

        row.addWidget(QLabel("COM Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(220)
        row.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        row.addWidget(self.refresh_btn)

        row.addWidget(QLabel("Baud Rate:"))
        self.baud_combo = QComboBox()
        for b in config.AVAILABLE_BAUDRATES:
            self.baud_combo.addItem(str(b))
        self.baud_combo.setCurrentText(str(config.DEFAULT_BAUDRATE))
        row.addWidget(self.baud_combo)

        self.simulate_checkbox = QCheckBox("Simulate (no hardware)")
        self.simulate_checkbox.stateChanged.connect(self._on_simulate_toggled)
        row.addWidget(self.simulate_checkbox)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        row.addWidget(self.connect_btn)

        row.addStretch()
        return row

    def _build_record_bar(self):
        row = QHBoxLayout()

        self.record_btn = QPushButton("● Record")
        self.record_btn.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.record_btn.clicked.connect(self._on_record_clicked)
        row.addWidget(self.record_btn)

        self.stop_btn = QPushButton("■ Stop && Export")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        row.addWidget(self.stop_btn)

        self.record_status_label = QLabel("Not recording")
        row.addWidget(self.record_status_label)

        row.addStretch()

        self.export_settings_btn = QPushButton("Export Current Settings")
        self.export_settings_btn.clicked.connect(self._on_export_settings_clicked)
        row.addWidget(self.export_settings_btn)

        return row

    def _build_sensor_grid(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(10)

        self.sensor_widgets = []
        cols = 3  # 3 columns -> 7 sensors => rows of 3,3,1
        for i in range(config.NUM_SENSORS):
            sw = SensorWidget(index=i, name=config.SENSOR_NAMES[i])
            sw.calibration_changed.connect(self._on_calibration_changed)
            self.sensor_widgets.append(sw)
            grid.addWidget(sw, i // cols, i % cols)

        scroll.setWidget(container)
        return scroll

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

    def _on_simulate_toggled(self, state):
        is_sim = bool(state)
        self.port_combo.setEnabled(not is_sim)
        self.refresh_btn.setEnabled(not is_sim)
        self.baud_combo.setEnabled(not is_sim)

    def _on_connect_clicked(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        if self.simulate_checkbox.isChecked():
            self.simulator = SimulatedSource()
            self.simulator.data_received.connect(self._on_data_received)
            self.simulator.status_changed.connect(self.statusBar().showMessage)
            self.simulator.start()
            self.connected = True
            self.connect_btn.setText("Disconnect")
            self._set_connection_controls_enabled(False)
            return

        device = self.port_combo.currentData()
        if not device:
            QMessageBox.warning(self, "No Port Selected", "Please select a valid COM port, or enable Simulate mode.")
            return
        baud = int(self.baud_combo.currentText())

        self.worker = SerialWorker(device, baud)
        self.worker.data_received.connect(self._on_data_received)
        self.worker.status_changed.connect(self.statusBar().showMessage)
        self.worker.settings_line_received.connect(self._on_settings_line_received)
        self.worker.start()

        self.connected = True
        self.connect_btn.setText("Disconnect")
        self._set_connection_controls_enabled(False)

    def _disconnect(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        if self.simulator is not None:
            self.simulator.stop()
            self.simulator = None

        self.connected = False
        self.connect_btn.setText("Connect")
        self._set_connection_controls_enabled(True)
        self.statusBar().showMessage("Disconnected")

    def _set_connection_controls_enabled(self, enabled: bool):
        self.port_combo.setEnabled(enabled and not self.simulate_checkbox.isChecked())
        self.refresh_btn.setEnabled(enabled and not self.simulate_checkbox.isChecked())
        self.baud_combo.setEnabled(enabled and not self.simulate_checkbox.isChecked())
        self.simulate_checkbox.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Live data + calibration
    # ------------------------------------------------------------------
    def _on_data_received(self, values):
        self.last_values = values
        for sw, v in zip(self.sensor_widgets, values):
            sw.add_sample(v)
        if self.recorder.is_recording:
            self.recorder.write_sample(values)
            self.record_status_label.setText(
                f"Recording... {self.recorder.sample_count} samples"
            )

    def _on_calibration_changed(self, index: int, value: float):
        index_1_based = index + 1
        source = self.worker if self.worker is not None else self.simulator
        if source is None:
            return
        ok = source.send_calibration(index_1_based, value)
        msg = (
            f"Sent calibration for {config.SENSOR_NAMES[index]}: {value:.2f}"
            if ok
            else "Failed to send calibration (not connected?)"
        )
        self.statusBar().showMessage(msg, 3000)

    def _on_settings_line_received(self, index_1_based: int, value: float):
        idx = index_1_based - 1
        if 0 <= idx < len(self.sensor_widgets):
            self.sensor_widgets[idx].set_calibration_silent(value)

    # ------------------------------------------------------------------
    # Recording / export
    # ------------------------------------------------------------------
    def _on_record_clicked(self):
        if not self.connected:
            QMessageBox.warning(self, "Not Connected", "Connect to a device (or enable Simulate mode) before recording.")
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
            # user cancelled the save dialog - keep data available, don't discard silently
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

        calibration_values = [sw.current_calibration() for sw in self.sensor_widgets]
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

    def _on_export_settings_clicked(self):
        calibration_values = [sw.current_calibration() for sw in self.sensor_widgets]
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

    def _current_port_info(self):
        if self.simulate_checkbox.isChecked():
            return {"port": "SIMULATED", "baudrate": "-"}
        return {
            "port": self.port_combo.currentData() or "",
            "baudrate": self.baud_combo.currentText(),
        }

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
