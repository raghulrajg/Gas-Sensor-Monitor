"""
config.py
---------
Central place for all tunable constants used across the application.
"""

# ---------------------------------------------------------------------------
# Serial communication
# ---------------------------------------------------------------------------
BAUDRATE = 921600  # hardcoded per device spec
SERIAL_READ_TIMEOUT = 1.0     # seconds, blocking read timeout inside worker thread
SERIAL_WRITE_TIMEOUT = 1.0

# --- Wire protocol -----------------------------------------------------
# Incoming data line from the device (one line per sample), e.g.:
#   D:12.30,45.60,7.80,0.00,23.40,56.70,89.00,24.50,55.20
# i.e. "D:" followed by 7 gas values, then temperature, then humidity
# (9 comma separated float values total, in that order), terminated with '\n'.
DATA_LINE_PREFIX = "D:"

# Outgoing calibration command sent to the device when a gas sensor slider
# changes (only the 7 gas sensors are calibratable):
#   C:<sensor_index_1_based>:<value>\n
# Example: "C:3:25.50\n" sets gas sensor 3's calibration value to 25.50
CALIBRATION_CMD_FMT = "C:{index}:{value:.2f}\n"

# Optional: ask the device to report its current settings, device is expected
# to reply with lines formatted like "C:<index>:<value>"
REQUEST_SETTINGS_CMD = "R:SETTINGS\n"

# ---------------------------------------------------------------------------
# Channels: 7 calibratable gas sensors + temperature + humidity
# ---------------------------------------------------------------------------
# gas_index is the 1-based index used in the calibration wire protocol.
# color is the default plot line color (hex); user can change this at
# runtime from the View > Line Colors menu.
CHANNELS = [
    {"key": "gas1", "name": "Sensor 1", "unit": "ppm", "calibration": True, "gas_index": 1, "color": "#1f77b4"},
    {"key": "gas2", "name": "Sensor 2", "unit": "ppm", "calibration": True, "gas_index": 2, "color": "#ff7f0e"},
    {"key": "gas3", "name": "Sensor 3", "unit": "ppm", "calibration": True, "gas_index": 3, "color": "#2ca02c"},
    {"key": "gas4", "name": "Sensor 4", "unit": "ppm", "calibration": True, "gas_index": 4, "color": "#d62728"},
    {"key": "gas5", "name": "Sensor 5", "unit": "ppm", "calibration": True, "gas_index": 5, "color": "#9467bd"},
    {"key": "gas6", "name": "Sensor 6", "unit": "ppm", "calibration": True, "gas_index": 6, "color": "#8c564b"},
    {"key": "gas7", "name": "Sensor 7", "unit": "ppm", "calibration": True, "gas_index": 7, "color": "#e377c2"},
    {"key": "temp", "name": "Temperature", "unit": "\u00b0C", "calibration": False, "gas_index": None, "color": "#17becf"},
    {"key": "humidity", "name": "Humidity", "unit": "%RH", "calibration": False, "gas_index": None, "color": "#bcbd22"},
]

NUM_CHANNELS = len(CHANNELS)               # 9 - total data values per incoming line
GAS_SENSOR_COUNT = sum(1 for c in CHANNELS if c["calibration"])  # 7

# ---------------------------------------------------------------------------
# Live plotting
# ---------------------------------------------------------------------------
# Number of most-recent points kept & drawn per channel. This bounds memory
# and render cost so the UI can never bog down / crash no matter how long
# the app has been running. Recording (Excel export) is NOT limited by this.
PLOT_BUFFER_SIZE = 300

# ---------------------------------------------------------------------------
# Calibration slider range (gas sensors only)
# ---------------------------------------------------------------------------
CALIBRATION_MIN = 0.0
CALIBRATION_MAX = 100.0
CALIBRATION_STEP = 0.1
CALIBRATION_DEFAULT = 0.0

# Debounce time (ms) - we wait this long after the user stops moving the
# slider before actually sending the value over serial, to avoid flooding
# the device with a command for every intermediate pixel of drag.
CALIBRATION_SEND_DEBOUNCE_MS = 200

# ---------------------------------------------------------------------------
# Layout defaults (changeable at runtime via View > Graph Layout)
# ---------------------------------------------------------------------------
DEFAULT_GRID_COLUMNS = 3

# ---------------------------------------------------------------------------
# Theme defaults (changeable at runtime via View > Application Theme)
# ---------------------------------------------------------------------------
THEME_PRESETS = {
    "Light": {"background": "#f5f6fa", "text": "#2c3e50", "card": "#ffffff"},
    "Dark": {"background": "#1e1e2e", "text": "#e0e0e0", "card": "#2b2b3c"},
}
DEFAULT_THEME = "Light"
