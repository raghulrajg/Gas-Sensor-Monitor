"""
simulator.py
------------
Generates fake sensor data on a QTimer so the whole UI (graphs, recording,
Excel export) can be exercised without any hardware attached. Mirrors the
same signal interface as SerialWorker (`data_received`, `status_changed`)
so MainWindow can treat both interchangeably.
"""

import math
import random
import time

from PySide6.QtCore import QObject, QTimer, Signal

import config


class SimulatedSource(QObject):
    data_received = Signal(list)
    status_changed = Signal(str)
    settings_line_received = Signal(int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._emit_sample)
        self._t0 = time.time()
        self._offsets = [random.uniform(0, 6.28) for _ in range(config.NUM_SENSORS)]
        self._calibration = [config.CALIBRATION_DEFAULT] * config.NUM_SENSORS

    def start(self):
        self._timer.start(config.SIMULATION_INTERVAL_MS)
        self.status_changed.emit("Simulation running (no hardware connected)")

    def stop(self):
        self._timer.stop()
        self.status_changed.emit("Simulation stopped")

    # Mirrors SerialWorker API so MainWindow code paths are identical
    def send_calibration(self, index_1_based: int, value: float) -> bool:
        self._calibration[index_1_based - 1] = value
        return True

    def send_raw(self, text: str) -> bool:
        return True

    def _emit_sample(self):
        t = time.time() - self._t0
        values = []
        for i in range(config.NUM_SENSORS):
            base = 20 + 15 * math.sin(t * 0.3 + self._offsets[i])
            noise = random.uniform(-1.5, 1.5)
            values.append(round(base + noise + self._calibration[i] * 0.1, 2))
        self.data_received.emit(values)
