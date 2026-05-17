"""
PrimitiveGrid — scrollable icon grid for a category tab in the left sidebar.

Primitives are arranged in a QGridLayout.  Category section headers are
shown only when the grid displays more than one category.

Icon size is changed via right-click context menu on empty grid space.

Each button supports:
  Left-click         → primitive_add(name)
  Right-click menu   → Add / Insert Before / Insert After
                       ("Insert" entries shown only when a selection exists)

Signals
-------
  primitive_add(str)
  primitive_insert_before(str)
  primitive_insert_after(str)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QMenu,
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
    primitive_add           = Signal(str)
    primitive_insert_before = Signal(str)
    primitive_insert_after  = Signal(str)

    def __init__(
        self,
        loader: PrimitivePluginLoader,
        model=None,               # Optional[EditorModel] — for selection awareness
        categories: Optional[list[str]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._loader     = loader
        self._model      = model
        self._categories = categories
        self._icon_px    = 44

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        root.addWidget(scroll)

        self._grid_widget = QWidget()
        self._grid_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._grid_widget.customContextMenuRequested.connect(self._size_context_menu)

        self._grid_layout = QVBoxLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        self._grid_layout.setSpacing(6)
        scroll.setWidget(self._grid_widget)

        self._rebuild()

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    def _size_context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addSection("Размер на иконите")
        for label, px in _SIZES.items():
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(self._icon_px == px)
            act.triggered.connect(lambda _=False, p=px: self._set_size(p))
        menu.exec(self._grid_widget.mapToGlobal(pos))

    def _button_context_menu(self, pos, name: str, btn: QToolButton) -> None:
        menu = QMenu(self)
        menu.addAction("Добави", lambda: self.primitive_add.emit(name))
        if self._has_selection():
            menu.addSeparator()
            menu.addAction("Вмъкни преди", lambda: self.primitive_insert_before.emit(name))
            menu.addAction("Вмъкни след",  lambda: self.primitive_insert_after.emit(name))
        menu.exec(btn.mapToGlobal(pos))

    def _has_selection(self) -> bool:
        return (
            self._model is not None
            and getattr(self._model, "selected_op",  -1) >= 0
            and getattr(self._model, "selected_seq", -1) >= 0
        )

    # ------------------------------------------------------------------
    # Size change
    # ------------------------------------------------------------------

    def _set_size(self, px: int) -> None:
        self._icon_px = px
        self._rebuild()

    # ------------------------------------------------------------------
    # Rebuild grid
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        groups = self._loader.by_category()
        order  = _CAT_ORDER + sorted(k for k in groups if k not in _CAT_ORDER)

        if self._categories:
            order = [c for c in order if c in self._categories]

        visible = [c for c in order if groups.get(c)]
        show_headers = len(visible) > 1
        cols = max(1, 180 // (self._icon_px + 8))

        for cat in visible:
            prims = groups.get(cat, [])

            if show_headers:
                lbl = QLabel(_CAT_LABELS.get(cat, cat))
                lbl.setStyleSheet(
                    "color:#90A4AE; font-size:10px; font-weight:bold;"
                    "border-bottom:1px solid #37474F; padding-bottom:2px;"
                )
                self._grid_layout.addWidget(lbl)

            row_widget = QWidget()
            row_layout = QGridLayout(row_widget)
            row_layout.setSpacing(4)
            row_layout.setContentsMargins(0, 0, 0, 0)

            for idx, p in enumerate(prims):
                btn = QToolButton()
                btn.setIcon(_render_icon(p, self._icon_px))
                btn.setIconSize(QSize(self._icon_px, self._icon_px))
                btn.setToolTip(f"<b>{p.display_name}</b><br>{p.tooltip}")
                btn.setFixedSize(self._icon_px + 8, self._icon_px + 8)
                btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

                name = p.name
                btn.clicked.connect(
                    lambda _=False, n=name: self.primitive_add.emit(n)
                )
                btn.customContextMenuRequested.connect(
                    lambda pos, n=name, b=btn: self._button_context_menu(pos, n, b)
                )
                row_layout.addWidget(btn, idx // cols, idx % cols)

            self._grid_layout.addWidget(row_widget)

        self._grid_layout.addStretch()
