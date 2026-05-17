"""
LeftSidebar — QTabWidget with one tab per operation category.

Tabs (in order):
  0: Подготовка  → Setup + Machine
  1: Пробиване   → Drilling
  2: Външни      → External + Turning
  3: Вътрешни    → Internal

Each tab is a PrimitiveGrid filtered to its category group.

Signals
-------
  primitive_add(str)
  primitive_insert_before(str)
  primitive_insert_after(str)
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget

from ui.editor_model import EditorModel
from ui.primitive_grid import PrimitiveGrid

_TABS: list[tuple[str, list[str]]] = [
    ("Подготовка", ["Setup", "Machine"]),
    ("Пробиване",  ["Drilling"]),
    ("Външни",     ["External", "Turning"]),
    ("Вътрешни",   ["Internal"]),
]


class LeftSidebar(QTabWidget):
    primitive_add           = Signal(str)
    primitive_insert_before = Signal(str)
    primitive_insert_after  = Signal(str)

    def __init__(self, model: EditorModel, parent=None) -> None:
        super().__init__(parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setMinimumWidth(200)
        self.setMaximumWidth(320)

        for label, cats in _TABS:
            grid = PrimitiveGrid(
                loader=model.loader,
                model=model,
                categories=cats,
                parent=self,
            )
            grid.primitive_add.connect(self.primitive_add)
            grid.primitive_insert_before.connect(self.primitive_insert_before)
            grid.primitive_insert_after.connect(self.primitive_insert_after)
            self.addTab(grid, label)

        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #1E272E;
            }
            QTabBar::tab {
                background: #263238;
                color: #90A4AE;
                padding: 5px 10px;
                border: none;
                border-right: 1px solid #1E272E;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #37474F;
                color: #ECEFF1;
                border-bottom: 2px solid #4FC3F7;
            }
            QTabBar::tab:hover:!selected {
                background: #2E3C43;
            }
        """)
