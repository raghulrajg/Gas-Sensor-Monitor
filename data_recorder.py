"""
data_recorder.py
-----------------
Handles "Record" -> "Stop -> Export to Excel" for the raw incoming gas
data stream.

Design note: this is intentionally decoupled from the live-plot ring
buffers (see sensor_widget.py). The graphs only ever keep the last
N points so the UI stays smooth, but every single sample that arrives
while recording is active is appended here using openpyxl's write-only
streaming mode. Write-only mode writes rows straight through without
holding the whole sheet in memory, so a multi-hour recording will not
balloon RAM usage or slow the UI down.
"""

import datetime as _dt

from openpyxl import Workbook
from openpyxl.styles import Font

import config


class DataRecorder:
    def __init__(self):
        self._wb = None
        self._ws = None
        self._recording = False
        self._sample_count = 0
        self._start_time = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def sample_count(self) -> int:
        return self._sample_count

    @property
    def start_time(self):
        return self._start_time

    def start(self):
        """Begin a new recording session (in-memory, streamed on write)."""
        self._wb = Workbook(write_only=True)
        self._ws = self._wb.create_sheet(title="Gas Data")
        header = ["Timestamp", "Elapsed (s)"] + [
            f"{name} ({config.SENSOR_UNITS})" for name in config.SENSOR_NAMES
        ]
        self._ws.append(header)
        self._sample_count = 0
        self._start_time = _dt.datetime.now()
        self._recording = True

    def write_sample(self, values):
        """Append one sample row. `values` is a list of NUM_SENSORS floats."""
        if not self._recording or self._ws is None:
            return
        now = _dt.datetime.now()
        elapsed = (now - self._start_time).total_seconds()
        row = [now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], round(elapsed, 2)] + list(values)
        self._ws.append(row)
        self._sample_count += 1

    def stop_and_save(self, filepath: str, calibration_values=None, port_info=None):
        """Finalize the recording and write the .xlsx file to `filepath`.

        Optionally appends a second sheet with the calibration/settings
        snapshot that was active during this recording.
        """
        if self._wb is None:
            raise RuntimeError("No active recording to save.")

        if calibration_values is not None:
            self._append_settings_sheet(calibration_values, port_info)

        if not filepath.lower().endswith(".xlsx"):
            filepath += ".xlsx"

        self._wb.save(filepath)

        self._recording = False
        result = (filepath, self._sample_count)
        self._wb = None
        self._ws = None
        return result

    def discard(self):
        """Abandon the current recording without saving."""
        self._wb = None
        self._ws = None
        self._recording = False
        self._sample_count = 0

    def _append_settings_sheet(self, calibration_values, port_info):
        ws2 = self._wb.create_sheet(title="Settings Snapshot")
        ws2.append(["Recording exported", _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        if port_info:
            ws2.append(["COM Port", port_info.get("port", "")])
            ws2.append(["Baud Rate", port_info.get("baudrate", "")])
        ws2.append([])
        ws2.append(["Sensor", f"Calibration Value ({config.SENSOR_UNITS})"])
        for name, val in zip(config.SENSOR_NAMES, calibration_values):
            ws2.append([name, val])


def export_settings_only(filepath: str, calibration_values, port_info=None):
    """Standalone export of just the current calibration/settings (no
    recorded data), used by the "Export Settings" button.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Settings"
    bold = Font(bold=True)

    ws.append(["Gas Sensor Monitor - Settings Export"])
    ws["A1"].font = bold
    ws.append(["Exported", _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    if port_info:
        ws.append(["COM Port", port_info.get("port", "")])
        ws.append(["Baud Rate", port_info.get("baudrate", "")])
    ws.append([])
    ws.append(["Sensor", f"Calibration Value ({config.SENSOR_UNITS})"])
    ws["A6"].font = bold
    ws["B6"].font = bold
    for name, val in zip(config.SENSOR_NAMES, calibration_values):
        ws.append([name, val])

    if not filepath.lower().endswith(".xlsx"):
        filepath += ".xlsx"
    wb.save(filepath)
    return filepath
