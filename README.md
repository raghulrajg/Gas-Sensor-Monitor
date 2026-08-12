# Gas Sensor Monitor

Desktop app for monitoring 7 digitally-calibrated gas sensors plus
temperature and humidity, over a USB serial connection: live time-based
graphs, per-sensor calibration sliders, recording to Excel, and
importable/exportable calibration profiles.

## Features

- **9 live graphs**: 7 gas sensors (each with a calibration
  slider/spinbox underneath) plus temperature and humidity (display only).
  X-axis is elapsed time in seconds, Y-axis is the reading (ppm / °C / %RH).
- **Bounded live buffers** — each graph only keeps the most recent
  `PLOT_BUFFER_SIZE` points (default 300). Old points drop off
  automatically, so the UI stays smooth no matter how long the app runs.
- **Clear Graphs** button — wipes all 9 graphs and resets the time axis
  back to zero, without touching an in-progress recording.
- **Recording is independent of the graph buffer.** Press **Record** and
  every incoming sample streams straight to a disk-backed Excel workbook
  (openpyxl "write-only" mode) — nothing is dropped or limited by what
  the graph is currently showing. Press **Stop & Export** to pick a save
  location; a second sheet in that file captures the calibration values
  active during the recording.
- **Export / Import Settings** (File menu) — export the 7 sensors'
  current calibration to its own `.xlsx`, or import a previously
  exported file to instantly re-apply (and re-send to the device) the
  same calibration profile — handy when you run the same setup
  repeatedly.
- **Calibration → device**: dragging a slider (or typing in the spinbox)
  sends the new value out over the serial port, debounced so it doesn't
  flood the link while you drag.
- **View menu**:
  - *Line Colors* — pick a new plot color for any of the 9 graphs.
  - *Application Theme* — Light/Dark presets or fully custom
    background/text/card colors.
  - *Graph Layout* — change the grid's column count and drag-reorder
    which graph appears where.

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.9+.

### Windows virtual environment

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

1. Pick the COM port (baud rate is fixed at **921600** — change in
   `config.py` if your device uses a different rate) and click **Connect**.
2. Drag any gas sensor's calibration slider — the new value is sent to
   the device automatically.
3. Click **● Record** to start logging, **■ Stop & Export** to save the
   session as an Excel file. **Clear Graphs** resets the live view at
   any time without affecting an active recording.
4. Use **File → Export/Import Settings** to save or reload a calibration
   profile.
5. Use **View** to customize line colors, theme, and graph layout.

## Serial protocol

Adjust to match your device's actual firmware — the parsing regex and
command format all live in `config.py` / `serial_worker.py`.

### Device → App (incoming sensor data)

One line per sample, newline terminated, 9 comma-separated values:
**7 gas readings, then temperature, then humidity**:

```
D:12.30,45.60,7.80,0.00,23.40,56.70,89.00,24.50,55.20
```

### App → Device (calibration command, gas sensors only)

Sent whenever a slider/spinbox value settles:

```
C:3:25.50
```

Meaning: set gas Sensor 3's calibration to 25.50. Format string is
`config.CALIBRATION_CMD_FMT`.

### Device → App (settings echo, optional)

If your firmware reports back current calibration on request/boot, send
lines in the same `C:<index>:<value>` format and the app updates the
matching slider (without re-sending it, avoiding a loop).

## Project layout

```
config.py          All tunable constants (baud rate, channel list, buffer size, ranges, theme presets...)
serial_worker.py    Background thread owning the real serial port (read + write)
sensor_widget.py     One graph (+ calibration slider, if applicable) widget, reused x9
data_recorder.py     Streaming Excel writer for Record/Stop, plus settings export/import
dialogs.py            Line color / theme / layout customization dialogs (View menu)
main_window.py        Top-level window: menu bar, connection bar, grid, recording
main.py                Entry point
```

## Adapting to your hardware

Hardware-specific bits are isolated in two places:

- **`config.py`** — channel list (`CHANNELS`), baud rate, calibration
  min/max/step, buffer size, protocol strings.
- **`serial_worker.py`** — `_parse_line()` (incoming data format) and
  `send_calibration()` / `CALIBRATION_CMD_FMT` (outgoing command format).

If your device uses a different framing, only those two spots need to
change — the rest of the app (graphs, recording, export, theming) is
unaffected.
