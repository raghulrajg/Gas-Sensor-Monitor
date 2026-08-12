# Gas Sensor Monitor

Desktop app for monitoring 7 digitally-calibrated gas sensors over a USB
serial connection: live graphs, per-sensor calibration sliders, and
recording to Excel.

## Features

- **7 live graphs**, one per sensor, each with its own calibration
  slider/spinbox underneath.
- **Bounded live buffers** — each graph only keeps the most recent
  `PLOT_BUFFER_SIZE` points (default 300). Old points drop off
  automatically as new ones arrive, so the UI stays smooth no matter
  how long the app runs (plotting unlimited points is what causes
  these kinds of apps to slow down or crash).
- **Recording is independent of the graph buffer.** Press **Record**
  and every single incoming sample is streamed straight to a disk-backed
  Excel workbook (openpyxl "write-only" mode) — nothing is dropped or
  limited by what the graph is currently showing, and memory use stays
  flat even for very long recordings. Press **Stop & Export** to pick a
  save location and finish the `.xlsx` file (a second sheet in that file
  captures the calibration settings that were active during the
  recording).
- **Export Current Settings** — dumps the current calibration value for
  all 7 sensors (plus port/baud info) to its own `.xlsx` file at any time,
  independent of recording.
- **Calibration → device**: dragging a slider (or typing in the spinbox)
  sends the new value out over the serial port, debounced so it doesn't
  flood the link while you drag.
- **Simulate mode** — tick "Simulate (no hardware)" to generate
  realistic fake data, so you can try out the whole app (including
  recording/export) before your hardware is connected.

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.9+.

## Run

```bash
venv\Scripts\activate
python main.py
```

1. Pick the COM port and baud rate (default 9600 — matches most common
   USB-serial gas sensor boards; change in `config.py` if your device
   uses a different default), or tick **Simulate** to try it without
   hardware.
2. Click **Connect**.
3. Drag any sensor's calibration slider — the new value is sent to the
   device automatically.
4. Click **● Record** to start logging, **■ Stop & Export** to save the
   session as an Excel file.
5. **Export Current Settings** any time to snapshot just the calibration
   values.

## Serial protocol

This app assumes a simple text line protocol. **Adjust to match your
device's actual firmware** — the parsing regexes and command format all
live in `config.py` / `serial_worker.py` so they're easy to change.

### Device → App (incoming sensor data)

One line per sample, newline terminated:

```
D:12.30,45.60,7.80,0.00,23.40,56.70,89.00
```

`D:` followed by 7 comma-separated float values, in sensor order
(Sensor 1 → Sensor 7).

### App → Device (calibration command)

Sent whenever a slider/spinbox value settles:

```
C:3:25.50
```

Meaning: set Sensor 3's calibration to 25.50. Format string is
`config.CALIBRATION_CMD_FMT`.

### Device → App (settings echo, optional)

If your firmware reports back current calibration on request/boot, send
lines in the same `C:<index>:<value>` format and the app will update the
matching slider (without re-sending it back out, avoiding a loop).

## Project layout

```
config.py          All tunable constants (sensor count, protocol, buffer size, ranges...)
serial_worker.py    Background thread owning the real serial port (read + write)
simulator.py         Fake data source with identical signal interface, for testing
sensor_widget.py     One graph + calibration slider widget, reused x7
data_recorder.py     Streaming Excel writer used for Record/Stop and Settings export
main_window.py       Top-level window wiring everything together
main.py               Entry point
```

## Adapting to your hardware

Almost everything hardware-specific is isolated in two places:

- **`config.py`** — sensor count/names, baud rate, calibration
  min/max/step, buffer size, protocol strings.
- **`serial_worker.py`** — `_parse_line()` (incoming data format) and
  `send_calibration()` / `CALIBRATION_CMD_FMT` (outgoing command format).

If your device uses a totally different framing (e.g. binary, or JSON
lines), only `_parse_line()` and `send_calibration()` need to change —
the rest of the app (graphs, recording, export) is unaffected.
