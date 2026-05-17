"""
PrimitiveGrid — scrollable icon grid for the left sidebar "Примитиви" tab.

Primitives are shown in a QGridLayout, grouped by category with a
section-header label.  An icon-size selector (small/medium/large) sits
at the top.  Clicking a button emits primitive_chosen(name).
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from domain.plugin_loader import PrimitivePluginLoader
from domain.primitive_base import LathePrimitive

_SIZES = {"Малки": 28, "Средни": 44, "Големи": 64}
_CAT_ORDER  = ["Setup", "Drilling", "External", "Turning", "Internal", "Machine"]
_CAT_LABELS = {
    "Setup":    "Подготовка",
    "Drilling": "Пробиване",
    "External": "Външни",
    "Turning":  "Струговане",
    "Internal": "Вътрешни",
    "Machine":  "Машина",
}


def _render_icon(primitive: LathePrimitive, size: int) -> QIcon:
    px = QPixmap(size, size)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    primitive.draw_icon(p, QRect(0, 0, size, size))
    p.end()
    return QIcon(px)


class PrimitiveGrid(QWidget):
    primitive_chosen = Signal(str)

    def __init__(self, loader: PrimitivePluginLoader, parent=None) -> None:
        super().__init__(parent)
        self._loader  = loader
        self._icon_px = 44   # default: medium

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # ── size selector ────────────────────────────────────────────
        top = QHBoxLayout()
        top.addWidget(QLabel("Размер:"))
        self._size_cb = QComboBox()
        for label in _SIZES:
            self._size_cb.addItem(label)
        self._size_cb.setCurrentIndex(1)
        self._size_cb.currentTextChanged.connect(self._on_size_changed)
        top.addWidget(self._size_cb)
        top.addStretch()
        root.addLayout(top)

        # ── scroll area with the grid ────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        root.addWidget(scroll)

        self._grid_widget = QWidget()
        self._grid_layout = QVBoxLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(2, 2, 2, 2)
        self._grid_layout.setSpacing(6)
        scroll.setWidget(self._grid_widget)

        self._rebuild()

    # ------------------------------------------------------------------

    def _on_size_changed(self, text: str) -> None:
        self._icon_px = _SIZES.get(text, 44)
        self._rebuild()

    def _rebuild(self) -> None:
        # clear
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        groups = self._loader.by_category()
        order  = _CAT_ORDER + sorted(k for k in groups if k not in _CAT_ORDER)

        cols = max(1, 180 // (self._icon_px + 8))

        for cat in order:
            prims = groups.get(cat)
            if not prims:
                continue
            lbl = QLabel(_CAT_LABELS.get(cat, cat))
            lbl.setStyleSheet(
                "color:#90A4AE; font-size:10px; font-weight:bold;"
                "border-bottom:1px solid #37474F; padding-bottom:2px;"
            )
            self._grid_layout.addWidget(lbl)

            row_widget  = QWidget()
            row_layout  = QGridLayout(row_widget)
            row_layout.setSpacing(4)
            row_layout.setContentsMargins(0, 0, 0, 0)

            for idx, p in enumerate(prims):
                btn = QToolButton()
                btn.setIcon(_render_icon(p, self._icon_px))
                btn.setIconSize(QSize(self._icon_px, self._icon_px))
                btn.setToolTip(f"<b>{p.display_name}</b><br>{p.tooltip}")
                btn.setFixedSize(self._icon_px + 8, self._icon_px + 8)
                name = p.name
                btn.clicked.connect(
                    lambda _=False, n=name: self.primitive_chosen.emit(n)
                )
                row_layout.addWidget(btn, idx // cols, idx % cols)

            self._grid_layout.addWidget(row_widget)

        self._grid_layout.addStretch()
