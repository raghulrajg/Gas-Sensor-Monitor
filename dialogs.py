"""
dialogs.py
----------
Small QDialogs used under the View menu to customize appearance:
  * LineColorDialog   - change each channel's plot line color (with a
                         per-row Reset and a Reset-All-to-Default)
  * ThemeDialog        - pick from a list of editor-style color schemes
                         (Light/Dark/Monokai/Dracula/Nord/...), or build a
                         fully custom background/text/card combination
  * LayoutDialog        - change graph grid column count and reorder channels

Note on signal connections: every slot below takes exactly the arguments
its signal provides (with a safe default for the rest), rather than a bare
lambda with a required leading parameter. That pattern is what caused the
"missing 1 required positional argument" crash previously - Qt's
signal/slot dispatch does not always forward the same number of arguments
in every context (e.g. `clicked()` vs `clicked(bool)`), so slots here are
written to tolerate being called with zero or one argument.
"""

from functools import partial

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QSpinBox,
    QColorDialog,
    QCheckBox,
    QDialogButtonBox,
    QFrame,
)

import config


def _swatch_icon(color: str, size: int = 16) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor(color))
    return QIcon(pix)


class ColorSwatchButton(QPushButton):
    """A small clickable colored square, used as a per-row color picker."""

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 22)
        self.set_color(color)

    def set_color(self, color: str):
        self.color = color
        self.setStyleSheet(
            f"background-color: {color}; border: 1px solid #888; border-radius: 3px;"
        )


class LineColorDialog(QDialog):
    """Lets the user pick a new plot line color for each channel. Applies
    immediately (live preview) via `on_color_changed(key, color)`."""

    def __init__(self, channel_colors: dict, on_color_changed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Graph Line Colors")
        self.setMinimumWidth(320)
        self._channel_colors = dict(channel_colors)
        self._on_color_changed = on_color_changed
        self._swatches = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Click a swatch to change that graph's line color:"))

        for ch in config.CHANNELS:
            row = QHBoxLayout()
            row.addWidget(QLabel(ch["name"]))
            row.addStretch()

            swatch = ColorSwatchButton(self._channel_colors.get(ch["key"], ch["color"]))
            swatch.clicked.connect(partial(self._pick_color, ch["key"], swatch))
            self._swatches[ch["key"]] = swatch
            row.addWidget(swatch)

            reset_btn = QPushButton("Reset")
            reset_btn.setToolTip("Reset this graph to its default color")
            reset_btn.clicked.connect(partial(self._reset_one, ch["key"]))
            row.addWidget(reset_btn)

            layout.addLayout(row)

        reset_all_btn = QPushButton("Reset All to Default")
        reset_all_btn.clicked.connect(self._reset_all)
        layout.addWidget(reset_all_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _pick_color(self, key: str, swatch: ColorSwatchButton, checked: bool = False):
        current = self._channel_colors.get(key, "#1f77b4")
        color = QColorDialog.getColor(QColor(current), self, "Pick color")
        if color.isValid():
            self._set_channel_color(key, color.name(), swatch)

    def _reset_one(self, key: str, checked: bool = False):
        default_color = config.DEFAULT_LINE_COLORS.get(key)
        if default_color:
            self._set_channel_color(key, default_color, self._swatches[key])

    def _reset_all(self, checked: bool = False):
        for key, swatch in self._swatches.items():
            default_color = config.DEFAULT_LINE_COLORS.get(key)
            if default_color:
                self._set_channel_color(key, default_color, swatch)

    def _set_channel_color(self, key: str, hex_color: str, swatch: ColorSwatchButton):
        self._channel_colors[key] = hex_color
        swatch.set_color(hex_color)
        self._on_color_changed(key, hex_color)


class ThemeDialog(QDialog):
    """Editor-style theme picker: choose from a list of named color
    schemes (each with a matching set of default line colors), or build a
    fully custom background/text/card combination. Applies immediately via
    `on_theme_changed(background_hex, text_hex, card_hex, line_colors=None)`.
    `line_colors`, when provided, is a dict of {channel_key: hex} the
    caller may apply alongside the theme.
    """

    def __init__(self, current_theme: dict, on_theme_changed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Theme")
        self.setMinimumWidth(340)
        self._on_theme_changed = on_theme_changed
        self._theme = dict(current_theme)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Color scheme:"))

        self.preset_list = QListWidget()
        self.preset_list.setIconSize(QSize(16, 16))
        for name, values in config.THEME_PRESETS.items():
            item = QListWidgetItem(_swatch_icon(values["background"]), name)
            self.preset_list.addItem(item)
        self.preset_list.itemClicked.connect(self._on_preset_clicked)
        layout.addWidget(self.preset_list)

        self.apply_line_colors_checkbox = QCheckBox("Also apply this scheme's default line colors")
        self.apply_line_colors_checkbox.setChecked(True)
        layout.addWidget(self.apply_line_colors_checkbox)

        layout.addWidget(QLabel("Custom:"))
        custom_row = QHBoxLayout()

        bg_btn = QPushButton("Background...")
        bg_btn.clicked.connect(self._pick_background)
        custom_row.addWidget(bg_btn)

        text_btn = QPushButton("Text...")
        text_btn.clicked.connect(self._pick_text)
        custom_row.addWidget(text_btn)

        card_btn = QPushButton("Card...")
        card_btn.clicked.connect(self._pick_card)
        custom_row.addWidget(card_btn)

        layout.addLayout(custom_row)

        reset_btn = QPushButton(f"Reset to App Default ({config.DEFAULT_THEME})")
        reset_btn.clicked.connect(self._reset_to_default)
        layout.addWidget(reset_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _on_preset_clicked(self, item: QListWidgetItem):
        values = config.THEME_PRESETS[item.text()]
        self._theme.update(values)
        line_colors = values.get("line_colors") if self.apply_line_colors_checkbox.isChecked() else None
        line_colors_dict = None
        if line_colors:
            line_colors_dict = {ch["key"]: c for ch, c in zip(config.CHANNELS, line_colors)}
        self._on_theme_changed(self._theme["background"], self._theme["text"], self._theme["card"], line_colors_dict)

    def _reset_to_default(self, checked: bool = False):
        values = config.THEME_PRESETS[config.DEFAULT_THEME]
        self._theme.update(values)
        line_colors_dict = {ch["key"]: c for ch, c in zip(config.CHANNELS, values["line_colors"])}
        self._on_theme_changed(self._theme["background"], self._theme["text"], self._theme["card"], line_colors_dict)

    def _pick_background(self, checked: bool = False):
        color = QColorDialog.getColor(QColor(self._theme.get("background", "#ffffff")), self, "Background Color")
        if color.isValid():
            self._theme["background"] = color.name()
            self._on_theme_changed(self._theme["background"], self._theme["text"], self._theme["card"])

    def _pick_text(self, checked: bool = False):
        color = QColorDialog.getColor(QColor(self._theme.get("text", "#000000")), self, "Text Color")
        if color.isValid():
            self._theme["text"] = color.name()
            self._on_theme_changed(self._theme["background"], self._theme["text"], self._theme["card"])

    def _pick_card(self, checked: bool = False):
        color = QColorDialog.getColor(QColor(self._theme.get("card", "#ffffff")), self, "Card Color")
        if color.isValid():
            self._theme["card"] = color.name()
            self._on_theme_changed(self._theme["background"], self._theme["text"], self._theme["card"])


class LayoutDialog(QDialog):
    """Lets the user change the number of grid columns and drag-reorder
    the graphs' display position. Applies on OK via
    `on_layout_changed(ordered_keys, columns)`."""

    def __init__(self, ordered_keys: list, columns: int, on_layout_changed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Graph Layout")
        self._on_layout_changed = on_layout_changed
        self._key_by_name = {ch["name"]: ch["key"] for ch in config.CHANNELS}
        self._name_by_key = {ch["key"]: ch["name"] for ch in config.CHANNELS}

        layout = QVBoxLayout(self)

        col_row = QHBoxLayout()
        col_row.addWidget(QLabel("Grid columns:"))
        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(1, 4)
        self.columns_spin.setValue(columns)
        col_row.addWidget(self.columns_spin)
        col_row.addStretch()
        layout.addLayout(col_row)

        layout.addWidget(QLabel("Drag to reorder graphs (top-left to bottom-right):"))
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        for key in ordered_keys:
            self.list_widget.addItem(self._name_by_key[key])
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_ok(self):
        ordered_keys = [
            self._key_by_name[self.list_widget.item(i).text()]
            for i in range(self.list_widget.count())
        ]
        self._on_layout_changed(ordered_keys, self.columns_spin.value())
        self.accept()
