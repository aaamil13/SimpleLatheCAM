"""
OperationTree — QTreeWidget showing the PartRecipe operation hierarchy.

Structure:
  ToolSequence (T01 · CSS 200 m/min)
    └ cylinder      ⌀30 × 50 mm
    └ chamfer       2×45°
  ToolSequence (T03 · G97 1200 rpm)
    └ fillet        R2

Clicking a row calls model.select(seq_idx, op_idx).
Right-click context menu: Delete, Enable/Disable, Move Up/Down.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
)

from domain.plugin_loader import PrimitivePluginLoader
from domain.recipe import OperationRecord, PartRecipe, ToolSequence
from ui.editor_model import EditorModel

_SEQ_FG  = QColor("#CFD8DC")
_OP_FG   = QColor("#B0BEC5")
_DIS_FG  = QColor("#546E7A")


def _seq_label(seq: ToolSequence) -> str:
    mode = "CSS" if seq.spindle_mode.value == "G96" else "G97"
    unit = "m/min" if mode == "CSS" else "rpm"
    return f"T{seq.tool_id:02d}  ·  {mode} {seq.spindle_value:.0f} {unit}"


def _op_summary(op: OperationRecord, loader: PrimitivePluginLoader) -> str:
    plugin = loader.get(op.primitive_name)
    name   = plugin.display_name if plugin else op.primitive_name
    param_str = "  ".join(
        f"{k}={v:.2g}" for k, v in list(op.params.items())[:3]
    )
    return f"{name}   {param_str}"


class OperationTree(QTreeWidget):

    def __init__(self, model: EditorModel, parent=None) -> None:
        super().__init__(parent)
        self._model  = model
        self._loader = model.loader

        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.customContextMenuRequested.connect(self._context_menu)
        self.itemSelectionChanged.connect(self._on_selection)
        model.recipe_changed.connect(self.refresh)
        model.selection_changed.connect(self._highlight)

        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self.blockSignals(True)
        self.clear()
        recipe = self._model.recipe
        for si, seq in enumerate(recipe.tool_sequences):
            seq_item = QTreeWidgetItem([_seq_label(seq)])
            seq_item.setForeground(0, _SEQ_FG)
            seq_item.setData(0, Qt.ItemDataRole.UserRole, (si, -1))
            for oi, op in enumerate(seq.operations):
                op_item = QTreeWidgetItem([_op_summary(op, self._loader)])
                fg = _DIS_FG if not op.enabled else _OP_FG
                op_item.setForeground(0, fg)
                op_item.setData(0, Qt.ItemDataRole.UserRole, (si, oi))
                seq_item.addChild(op_item)
            self.addTopLevelItem(seq_item)
            seq_item.setExpanded(True)
        self.blockSignals(False)

    def _highlight(self, seq_idx: int, op_idx: int) -> None:
        self.blockSignals(True)
        self.clearSelection()
        for ti in range(self.topLevelItemCount()):
            top = self.topLevelItem(ti)
            data = top.data(0, Qt.ItemDataRole.UserRole)
            if data[0] == seq_idx and op_idx < 0:
                top.setSelected(True)
                break
            for ci in range(top.childCount()):
                child = top.child(ci)
                d = child.data(0, Qt.ItemDataRole.UserRole)
                if d[0] == seq_idx and d[1] == op_idx:
                    child.setSelected(True)
                    break
        self.blockSignals(False)

    def _on_selection(self) -> None:
        items = self.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if data:
            self._model.select(data[0], data[1])

    def _context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None or data[1] < 0:
            return
        si, oi = data
        menu = QMenu(self)
        seq = self._model.recipe.tool_sequences[si]
        op  = seq.operations[oi]

        toggle = menu.addAction("Изключи" if op.enabled else "Включи")
        menu.addSeparator()
        move_up   = menu.addAction("Нагоре")
        move_down = menu.addAction("Надолу")
        menu.addSeparator()
        delete = menu.addAction("Изтрий")

        action = menu.exec(self.viewport().mapToGlobal(pos))
        if action == toggle:
            op.enabled = not op.enabled
            self._model._mutated(si, oi)
        elif action == move_up and oi > 0:
            seq.move(oi, oi - 1)
            self._model._mutated(si, oi - 1)
        elif action == move_down and oi < len(seq.operations) - 1:
            seq.move(oi, oi + 1)
            self._model._mutated(si, oi + 1)
        elif action == delete:
            seq.operations.pop(oi)
            new_oi = min(oi, len(seq.operations) - 1)
            self._model._mutated(si, new_oi)
