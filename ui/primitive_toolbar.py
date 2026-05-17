"""
PrimitiveToolbar — horizontal toolbar with one icon button per loaded plug-in.

Buttons are grouped by LathePrimitive.category with a vertical separator and
a small category label between groups.  Clicking a button emits
`primitive_chosen(name)` so the main window can add a new operation.

Icons are rendered once at construction by calling each plug-in's
draw_icon() into a QPixmap.

Category display order (others appear at the end alphabetically):
  Setup → Drilling → External → Turning → Internal → Machine
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from domain.plugin_loader import PrimitivePluginLoader
from domain.primitive_base import LathePrimitive

_ICON_SIZE  = 36
_CAT_ORDER  = ["Setup", "Drilling", "External", "Turning", "Internal", "Machine"]

_CAT_LABELS = {
    "Setup":    "Подготовка",
    "Drilling": "Пробиване",
    "External": "Външни",
    "Turning":  "Струговане",
    "Internal": "Вътрешни",
    "Machine":  "Машина",
}


def _render_icon(primitive: LathePrimitive, size: int = _ICON_SIZE) -> QIcon:
    """Call primitive.draw_icon() into a QPixmap and return a QIcon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(45, 45, 45, 0))   # transparent dark background
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    primitive.draw_icon(painter, QRect(0, 0, size, size))
    painter.end()
    return QIcon(pixmap)


def _cat_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #888; font-size: 9px; padding: 0 4px;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class PrimitiveToolbar(QToolBar):
    """Toolbar that emits primitive_chosen(name) when a button is clicked."""

    primitive_chosen = Signal(str)

    def __init__(self, loader: PrimitivePluginLoader, parent=None) -> None:
        super().__init__("Primitives", parent)
        self.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self.setMovable(False)
        self.setObjectName("primitive_toolbar")
        self._loader = loader
        self._build(loader.by_category())

    def _build(self, groups: dict[str, list[LathePrimitive]]) -> None:
        # Ordered categories first, then any extras alphabetically
        order = _CAT_ORDER + sorted(
            k for k in groups if k not in _CAT_ORDER
        )
        first = True
        for cat in order:
            prims = groups.get(cat)
            if not prims:
                continue
            if not first:
                self.addSeparator()
            first = False
            lbl = _cat_label(_CAT_LABELS.get(cat, cat))
            self.addWidget(lbl)
            for p in prims:
                self._add_button(p)

    def _add_button(self, primitive: LathePrimitive) -> None:
        btn = QToolButton(self)
        btn.setIcon(_render_icon(primitive))
        btn.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        btn.setToolTip(f"<b>{primitive.display_name}</b><br>{primitive.tooltip}")
        btn.setStatusTip(primitive.display_name)
        btn.setCheckable(False)
        # Capture name in closure
        name = primitive.name
        btn.clicked.connect(lambda _=False, n=name: self.primitive_chosen.emit(n))
        self.addWidget(btn)
