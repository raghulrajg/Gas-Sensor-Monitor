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
# Each preset also ships a matching set of 9 line colors (one per channel,
# in CHANNELS order) chosen to stay readable against that theme's
# background - the same idea as a code editor's built-in color schemes.
THEME_PRESETS = {
    "Light": {
        "background": "#f5f6fa", "text": "#2c3e50", "card": "#ffffff", "border": "#d0d3d9",
        "line_colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                         "#8c564b", "#e377c2", "#17becf", "#bcbd22"],
    },
    "Dark": {
        "background": "#1e1e2e", "text": "#e0e0e0", "card": "#2b2b3c", "border": "#44445a",
        "line_colors": ["#3fa7ff", "#ffa552", "#4cd964", "#ff5c5c", "#c792ea",
                         "#d19a66", "#ff8fd1", "#56d4dd", "#e0d264"],
    },
    "Monokai": {
        "background": "#272822", "text": "#f8f8f2", "card": "#2f3129", "border": "#49483e",
        "line_colors": ["#f92672", "#fd971f", "#e6db74", "#a6e22e", "#66d9ef",
                         "#ae81ff", "#f8f8f2", "#75715e", "#a1efe4"],
    },
    "Dracula": {
        "background": "#282a36", "text": "#f8f8f2", "card": "#343746", "border": "#44475a",
        "line_colors": ["#ff5555", "#ffb86c", "#f1fa8c", "#50fa7b", "#8be9fd",
                         "#bd93f9", "#ff79c6", "#6272a4", "#ff92df"],
    },
    "Solarized Dark": {
        "background": "#002b36", "text": "#839496", "card": "#073642", "border": "#586e75",
        "line_colors": ["#b58900", "#cb4b16", "#dc322f", "#d33682", "#6c71c4",
                         "#268bd2", "#2aa198", "#859900", "#93a1a1"],
    },
    "Solarized Light": {
        "background": "#fdf6e3", "text": "#657b83", "card": "#eee8d5", "border": "#93a1a1",
        "line_colors": ["#b58900", "#cb4b16", "#dc322f", "#d33682", "#6c71c4",
                         "#268bd2", "#2aa198", "#859900", "#657b83"],
    },
    "Nord": {
        "background": "#2e3440", "text": "#d8dee9", "card": "#3b4252", "border": "#4c566a",
        "line_colors": ["#bf616a", "#d08770", "#ebcb8b", "#a3be8c", "#b48ead",
                         "#88c0d0", "#81a1c1", "#8fbcbb", "#5e81ac"],
    },
    "One Dark": {
        "background": "#282c34", "text": "#abb2bf", "card": "#21252b", "border": "#3e4451",
        "line_colors": ["#e06c75", "#d19a66", "#e5c07b", "#98c379", "#56b6c2",
                         "#61afef", "#c678dd", "#be5046", "#5c6370"],
    },
    "Gruvbox Dark": {
        "background": "#282828", "text": "#ebdbb2", "card": "#3c3836", "border": "#504945",
        "line_colors": ["#fb4934", "#fe8019", "#fabd2f", "#b8bb26", "#8ec07c",
                         "#83a598", "#d3869b", "#d65d0e", "#689d6a"],
    },
    "GitHub Light": {
        "background": "#ffffff", "text": "#24292e", "card": "#f6f8fa", "border": "#d0d7de",
        "line_colors": ["#d73a49", "#e36209", "#dbab09", "#28a745", "#0598bc",
                         "#0366d6", "#6f42c1", "#ea4aaa", "#6a737d"],
    },
}
DEFAULT_THEME = "Light"

# Fallback "factory default" line colors, independent of whichever theme is
# active - used by the Line Colors dialog's "Reset to Default" actions.
DEFAULT_LINE_COLORS = {ch["key"]: ch["color"] for ch in CHANNELS}
