"""
LeftSidebar — QTabWidget housing the primitives grid and operations tree.

Tab 0: "Примитиви" — PrimitiveGrid (scrollable icon browser by category)
Tab 1: "Операции"  — OperationTree (full recipe hierarchy with context menu)

Signals
-------
  primitive_chosen(str) — forwarded from PrimitiveGrid when a button is clicked
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget

from ui.editor_model import EditorModel
from ui.operation_tree import OperationTree
from ui.primitive_grid import PrimitiveGrid


class LeftSidebar(QTabWidget):
    primitive_chosen = Signal(str)

    def __init__(self, model: EditorModel, parent=None) -> None:
        super().__init__(parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setMinimumWidth(200)
        self.setMaximumWidth(320)

        self._primitives = PrimitiveGrid(model.loader, self)
        self._primitives.primitive_chosen.connect(self.primitive_chosen)
        self.addTab(self._primitives, "Примитиви")

        self._tree = OperationTree(model, self)
        self.addTab(self._tree, "Операции")

        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #1E272E;
            }
            QTabBar::tab {
                background: #263238;
                color: #90A4AE;
                padding: 6px 14px;
                border: none;
                border-right: 1px solid #1E272E;
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

    # ------------------------------------------------------------------
    # Convenience accessors

    @property
    def operation_tree(self) -> OperationTree:
        return self._tree

    def show_operations(self) -> None:
        """Switch to the Operations tab (called after adding an operation)."""
        self.setCurrentIndex(1)
