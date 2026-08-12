"""
sensor_widget.py
-----------------
One self-contained widget per channel (gas sensor, or temperature /
humidity):
  * a small live-updating pyqtgraph plot, x-axis = elapsed time (s),
    y-axis = the channel's reading, fed from a bounded ring buffer
    (collections.deque with maxlen) so plotting cost & memory never grow
    unbounded, no matter how long the app runs.
  * (gas sensors only) a calibration slider + spinbox kept in sync,
    which - after a short debounce - emits `calibration_changed(gas_index,
    value)` so the caller can push it out over serial.
"""

from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QDoubleSpinBox,
    QFrame,
)

import config


class SensorWidget(QFrame):
    # gas_index is the 1-based index used on the wire; only emitted for
    # channels that have calibration enabled.
    calibration_changed = Signal(int, float)

    def __init__(self, key: str, name: str, unit: str, calibration: bool,
                 gas_index=None, color: str = "#1f77b4", parent=None):
        super().__init__(parent)
        self.key = key
        self.name = name
        self.unit = unit
        self.has_calibration = calibration
        self.gas_index = gas_index
        self.color = color

        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("sensorCard")

        # Bounded buffers -> live plot never accumulates unbounded points.
        self._x_buffer = deque(maxlen=config.PLOT_BUFFER_SIZE)
        self._y_buffer = deque(maxlen=config.PLOT_BUFFER_SIZE)

        self._build_ui()

        # Debounce timer: only fire calibration_changed after the user
        # pauses moving the slider, to avoid flooding the serial link.
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_calibration)

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel(f"<b>{self.name}</b>")
        self.value_label = QLabel(f"-- {self.unit}")
        self.value_label.setAlignment(Qt.AlignRight)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.value_label)
        layout.addLayout(header)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(None)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.setLabel("left", self.unit)
        self.plot_widget.setLabel("bottom", "Time (s)")
        self.plot_widget.setMinimumHeight(150)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color=self.color, width=2))
        layout.addWidget(self.plot_widget)

        if self.has_calibration:
            cal_row = QHBoxLayout()
            cal_row.addWidget(QLabel("Calibration:"))

            self.slider = QSlider(Qt.Horizontal)
            self.slider.setMinimum(int(config.CALIBRATION_MIN / config.CALIBRATION_STEP))
            self.slider.setMaximum(int(config.CALIBRATION_MAX / config.CALIBRATION_STEP))
            self.slider.setValue(int(config.CALIBRATION_DEFAULT / config.CALIBRATION_STEP))
            self.slider.valueChanged.connect(self._on_slider_changed)
            cal_row.addWidget(self.slider, stretch=1)

            self.spinbox = QDoubleSpinBox()
            self.spinbox.setRange(config.CALIBRATION_MIN, config.CALIBRATION_MAX)
            self.spinbox.setSingleStep(config.CALIBRATION_STEP)
            self.spinbox.setDecimals(2)
            self.spinbox.setValue(config.CALIBRATION_DEFAULT)
            self.spinbox.valueChanged.connect(self._on_spinbox_changed)
            cal_row.addWidget(self.spinbox)

            layout.addLayout(cal_row)
        else:
            self.slider = None
            self.spinbox = None

    # ------------------------------------------------------------------
    # Slider / spinbox kept in sync, both funnel into the debounce timer
    # ------------------------------------------------------------------
    def _on_slider_changed(self, raw_value: int):
        value = raw_value * config.CALIBRATION_STEP
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(value)
        self.spinbox.blockSignals(False)
        self._restart_debounce()

    def _on_spinbox_changed(self, value: float):
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(value / config.CALIBRATION_STEP)))
        self.slider.blockSignals(False)
        self._restart_debounce()

    def _restart_debounce(self):
        self._debounce_timer.start(config.CALIBRATION_SEND_DEBOUNCE_MS)

    def _emit_calibration(self):
        self.calibration_changed.emit(self.gas_index, self.spinbox.value())

    def set_calibration_silent(self, value: float):
        """Update slider/spinbox from an external source (e.g. device
        reported its current settings, or an imported settings file)
        WITHOUT re-triggering a send."""
        if not self.has_calibration:
            return
        self.slider.blockSignals(True)
        self.spinbox.blockSignals(True)
        self.slider.setValue(int(round(value / config.CALIBRATION_STEP)))
        self.spinbox.setValue(value)
        self.slider.blockSignals(False)
        self.spinbox.blockSignals(False)

    def current_calibration(self) -> float:
        return self.spinbox.value() if self.has_calibration else 0.0

    # ------------------------------------------------------------------
    # Live data update
    # ------------------------------------------------------------------
    def add_sample(self, elapsed_seconds: float, value: float):
        self._x_buffer.append(elapsed_seconds)
        self._y_buffer.append(value)
        self.curve.setData(list(self._x_buffer), list(self._y_buffer))
        if value == value:  # not NaN
            self.value_label.setText(f"{value:.2f} {self.unit}")
        else:
            self.value_label.setText(f"-- {self.unit}")

    def clear_plot(self):
        self._x_buffer.clear()
        self._y_buffer.clear()
        self.curve.setData([], [])

    # ------------------------------------------------------------------
    # Appearance
    # ------------------------------------------------------------------
    def set_line_color(self, color: str):
        self.color = color
        self.curve.setPen(pg.mkPen(color=color, width=2))
