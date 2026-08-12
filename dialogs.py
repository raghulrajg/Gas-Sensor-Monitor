"""
dialogs.py
----------
Small QDialogs used under the View menu to customize appearance:
  * LineColorDialog   - change each channel's plot line color
  * ThemeDialog        - change the overall application background/text color
  * LayoutDialog        - change graph grid column count and reorder channels
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QAbstractItemView,
    QSpinBox,
    QColorDialog,
    QDialogButtonBox,
    QFrame,
)

import config


class ColorSwatch(QFrame):
    """A small clickable colored square."""

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 20)
        self.set_color(color)
        self.setFrameShape(QFrame.Box)

    def set_color(self, color: str):
        self.color = color
        self.setStyleSheet(f"background-color: {color}; border: 1px solid #888;")


class LineColorDialog(QDialog):
    """Lets the user pick a new plot line color for each channel. Applies
    immediately (live preview) via `on_color_changed(key, color)`."""

    def __init__(self, channel_colors: dict, on_color_changed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Graph Line Colors")
        self._channel_colors = dict(channel_colors)
        self._on_color_changed = on_color_changed
        self._swatches = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Click a swatch to change that graph's line color:"))

        for ch in config.CHANNELS:
            row = QHBoxLayout()
            row.addWidget(QLabel(ch["name"]))
            row.addStretch()
            swatch = ColorSwatch(self._channel_colors.get(ch["key"], ch["color"]))
            swatch.mousePressEvent = self._make_swatch_handler(ch["key"], swatch)
            self._swatches[ch["key"]] = swatch
            row.addWidget(swatch)
            layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _make_swatch_handler(self, key, swatch):
        def handler(event):
            current = self._channel_colors.get(key, "#1f77b4")
            color = QColorDialog.getColor(current, self, f"Pick color")
            if color.isValid():
                hex_color = color.name()
                self._channel_colors[key] = hex_color
                swatch.set_color(hex_color)
                self._on_color_changed(key, hex_color)

        return handler


class ThemeDialog(QDialog):
    """Lets the user pick an application-wide background/text theme, either
    from presets or a custom color pick. Applies immediately via
    `on_theme_changed(background_hex, text_hex, card_hex)`."""

    def __init__(self, current_theme: dict, on_theme_changed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Theme")
        self._on_theme_changed = on_theme_changed
        self._theme = dict(current_theme)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Presets:"))

        preset_row = QHBoxLayout()
        for name, values in config.THEME_PRESETS.items():
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, v=values: self._apply(v))
            preset_row.addWidget(btn)
        layout.addLayout(preset_row)

        layout.addWidget(QLabel("Custom:"))
        custom_row = QHBoxLayout()

        bg_btn = QPushButton("Background Color...")
        bg_btn.clicked.connect(self._pick_background)
        custom_row.addWidget(bg_btn)

        text_btn = QPushButton("Text Color...")
        text_btn.clicked.connect(self._pick_text)
        custom_row.addWidget(text_btn)

        card_btn = QPushButton("Card Color...")
        card_btn.clicked.connect(self._pick_card)
        custom_row.addWidget(card_btn)

        layout.addLayout(custom_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _apply(self, values):
        self._theme.update(values)
        self._on_theme_changed(self._theme["background"], self._theme["text"], self._theme["card"])

    def _pick_background(self):
        color = QColorDialog.getColor(self._theme.get("background", "#ffffff"), self, "Background Color")
        if color.isValid():
            self._theme["background"] = color.name()
            self._on_theme_changed(self._theme["background"], self._theme["text"], self._theme["card"])

    def _pick_text(self):
        color = QColorDialog.getColor(self._theme.get("text", "#000000"), self, "Text Color")
        if color.isValid():
            self._theme["text"] = color.name()
            self._on_theme_changed(self._theme["background"], self._theme["text"], self._theme["card"])

    def _pick_card(self):
        color = QColorDialog.getColor(self._theme.get("card", "#ffffff"), self, "Card Color")
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
