"""
config.py
---------
Central place for all tunable constants used across the application.
Change these to match your hardware / preferences without touching
the rest of the code.
"""

# ---------------------------------------------------------------------------
# Sensor setup
# ---------------------------------------------------------------------------
NUM_SENSORS = 7
SENSOR_NAMES = [f"Sensor {i + 1}" for i in range(NUM_SENSORS)]
SENSOR_UNITS = "ppm"  # shown on the y-axis / value labels

# ---------------------------------------------------------------------------
# Serial communication
# ---------------------------------------------------------------------------
DEFAULT_BAUDRATE = 9600
AVAILABLE_BAUDRATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
SERIAL_READ_TIMEOUT = 1.0     # seconds, blocking read timeout inside worker thread
SERIAL_WRITE_TIMEOUT = 1.0

# --- Wire protocol -----------------------------------------------------
# Incoming data line from the device (one line per sample), e.g.:
#   D:12.30,45.60,7.80,0.00,23.40,56.70,89.00
# i.e. "D:" followed by NUM_SENSORS comma separated float values, in order,
# terminated with '\n'.
DATA_LINE_PREFIX = "D:"

# Outgoing calibration command sent to the device when a slider changes:
#   C:<sensor_index_1_based>:<value>\n
# Example: "C:3:25.50\n" sets sensor 3's calibration value to 25.50
CALIBRATION_CMD_FMT = "C:{index}:{value:.2f}\n"

# Optional: ask the device to report its current settings, device is expected
# to reply with NUM_SENSORS lines formatted like "C:<index>:<value>"
REQUEST_SETTINGS_CMD = "R:SETTINGS\n"

# ---------------------------------------------------------------------------
# Live plotting
# ---------------------------------------------------------------------------
# Number of most-recent points kept & drawn per sensor. This bounds memory
# and render cost so the UI can never bog down / crash no matter how long
# the app has been running. Recording (Excel export) is NOT limited by this.
PLOT_BUFFER_SIZE = 300

# ---------------------------------------------------------------------------
# Calibration slider range
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
# Simulation mode (no hardware needed - useful for demo/testing the UI)
# ---------------------------------------------------------------------------
SIMULATION_INTERVAL_MS = 200
