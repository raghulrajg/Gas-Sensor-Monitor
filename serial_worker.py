"""
serial_worker.py
-----------------
Background QThread that owns the serial port. It:
  * continuously reads lines from the device and parses them into
    7 float values, emitted via the `data_received` signal.
  * exposes a thread-safe `send_calibration()` / `send_raw()` method the
    GUI thread can call to write commands (e.g. new calibration values)
    out to the device.

Kept deliberately separate from the GUI so a slow / stalled serial link
can never freeze the UI.
"""

import re
import time
import threading

import serial
from PySide6.QtCore import QThread, Signal

import config


class SerialWorker(QThread):
    # Emits a list of NUM_SENSORS floats, in sensor order.
    data_received = Signal(list)
    # Emits a human readable status / error string.
    status_changed = Signal(str)
    # Emitted specifically when the initial port open fails, so the caller
    # can distinguish "never actually connected" from a mid-session hiccup
    # and revert any optimistic "Connected" UI state.
    connection_failed = Signal(str)
    # Emitted with (index_1_based, value) when the device confirms/reports
    # a calibration value (used when importing current settings from device).
    settings_line_received = Signal(int, float)

    _DATA_RE = re.compile(r"^D:\s*(.+)$")
    _SETTINGS_RE = re.compile(r"^C:\s*(\d+)\s*:\s*([-+]?[0-9]*\.?[0-9]+)\s*$")

    def __init__(self, port: str, baudrate: int, parent=None):
        super().__init__(parent)
        self.port_name = port
        self.baudrate = baudrate
        self._serial = None
        self._running = False
        self._write_lock = threading.Lock()

    # ------------------------------------------------------------------
    # QThread main loop
    # ------------------------------------------------------------------
    def run(self):
        try:
            self._serial = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                timeout=config.SERIAL_READ_TIMEOUT,
                write_timeout=config.SERIAL_WRITE_TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"Failed to open {self.port_name}: {exc}"
            self.status_changed.emit(msg)
            self.connection_failed.emit(msg)
            return

        self._running = True
        self.status_changed.emit(f"Connected to {self.port_name} @ {self.baudrate} baud")

        while self._running:
            try:
                raw = self._serial.readline()
            except Exception as exc:  # noqa: BLE001
                self.status_changed.emit(f"Serial read error: {exc}")
                time.sleep(0.5)
                continue

            if not raw:
                continue  # timeout, no data this round - loop again

            try:
                line = raw.decode("utf-8", errors="ignore").strip()
            except Exception:  # noqa: BLE001
                continue

            if not line:
                continue

            self._parse_line(line)

        # cleanup
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
        except Exception:  # noqa: BLE001
            pass
        self.status_changed.emit("Disconnected")

    def _parse_line(self, line: str):
        data_match = self._DATA_RE.match(line)
        if data_match:
            parts = [p.strip() for p in data_match.group(1).split(",")]
            values = []
            for p in parts:
                try:
                    values.append(float(p))
                except ValueError:
                    values.append(float("nan"))
            # pad / trim to expected sensor count so a malformed line
            # never crashes the UI update
            if len(values) < config.NUM_CHANNELS:
                values.extend([float("nan")] * (config.NUM_CHANNELS - len(values)))
            elif len(values) > config.NUM_CHANNELS:
                values = values[: config.NUM_CHANNELS]
            self.data_received.emit(values)
            return

        settings_match = self._SETTINGS_RE.match(line)
        if settings_match:
            idx = int(settings_match.group(1))
            val = float(settings_match.group(2))
            self.settings_line_received.emit(idx, val)
            return
        # Unknown line format - ignore silently (could log if desired)

    # ------------------------------------------------------------------
    # Public control API (safe to call from GUI thread)
    # ------------------------------------------------------------------
    def stop(self):
        self._running = False
        self.wait(2000)

    def send_calibration(self, index_1_based: int, value: float) -> bool:
        cmd = config.CALIBRATION_CMD_FMT.format(index=index_1_based, value=value)
        return self.send_raw(cmd)

    def send_raw(self, text: str) -> bool:
        if not self._serial or not self._serial.is_open:
            return False
        try:
            with self._write_lock:
                self._serial.write(text.encode("utf-8"))
                self._serial.flush()
            return True
        except Exception as exc:  # noqa: BLE001
            self.status_changed.emit(f"Serial write error: {exc}")
            return False


def list_available_ports():
    """Return a list of (device, description) tuples for available COM ports."""
    from serial.tools import list_ports

    return [(p.device, p.description) for p in list_ports.comports()]
