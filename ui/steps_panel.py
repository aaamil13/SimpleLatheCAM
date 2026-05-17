"""
StepsPanel — right-side accordion list of machining steps.

Each ToolSequence is shown as a section header.
Each operation is a StepCard with:
  - enable/disable checkbox
  - name + param summary
  - gear button → OperationEditDialog (modal with ParamsPanel + coolant toggle)
  - delete button

Selecting a card calls model.select(seq_idx, op_idx).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from domain.machine import MachineConfig
from domain.recipe import OperationRecord, ToolSequence
from ui.editor_model import EditorModel
from ui.params_panel import ParamsPanel


# ---------------------------------------------------------------------------
# Edit dialog
# ---------------------------------------------------------------------------

class OperationEditDialog(QDialog):
    """Modal dialog: ParamsPanel + optional coolant toggle."""

    def __init__(
        self,
        model:    EditorModel,
        seq_idx:  int,
        op_idx:   int,
        machine:  Optional[MachineConfig] = None,
        parent:   Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._model   = model
        self._seq_idx = seq_idx
        self._op_idx  = op_idx

        seq    = model.recipe.tool_sequences[seq_idx]
        op     = seq.operations[op_idx]
        plugin = model.loader.get(op.primitive_name)

        self.setWindowTitle(plugin.display_name if plugin else op.primitive_name)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._panel = ParamsPanel(self)
        ctx = model.profile.context()
        self._panel.set_primitive(plugin, op.params, ctx)
        self._panel.params_changed.connect(self._on_params_changed)
        layout.addWidget(self._panel)

        # Coolant toggle — only if machine has coolant capability
        if machine is not None and machine.coolant_available:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #37474F;")
            layout.addWidget(sep)

            self._coolant_cb = QCheckBox("Охлаждане за тази операция")
            current = op.coolant_on if op.coolant_on is not None else seq.coolant_on
            self._coolant_cb.setChecked(bool(current))
            self._coolant_cb.setToolTip(
                "Включи/изключи охлаждане специфично за тази операция.\n"
                "Ако не е зададено, се наследява от настройките на инструмента."
            )
            self._coolant_cb.stateChanged.connect(self._on_coolant_changed)
            layout.addWidget(self._coolant_cb)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        btns.rejected.connect(self.accept)
        layout.addWidget(btns)

    def _on_params_changed(self, params: dict) -> None:
        self._model.select(self._seq_idx, self._op_idx)
        self._model.update_params(params)

    def _on_coolant_changed(self, state: int) -> None:
        self._model.select(self._seq_idx, self._op_idx)
        self._model.update_coolant_override(bool(state))


# ---------------------------------------------------------------------------
# Single step card
# ---------------------------------------------------------------------------

class StepCard(QFrame):
    selected = Signal(int, int)

    def __init__(
        self,
        model:    EditorModel,
        seq_idx:  int,
        op_idx:   int,
        op:       OperationRecord,
        machine:  Optional[MachineConfig] = None,
        parent:   Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._model   = model
        self._seq_idx = seq_idx
        self._op_idx  = op_idx
        self._op      = op
        self._machine = machine

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("StepCard")
        self._update_style(False)

        row = QHBoxLayout(self)
        row.setContentsMargins(4, 3, 4, 3)
        row.setSpacing(4)

        self._check = QCheckBox()
        self._check.setChecked(op.enabled)
        self._check.setToolTip("Включи / изключи стъпката")
        self._check.stateChanged.connect(self._toggle_enabled)
        row.addWidget(self._check)

        plugin = model.loader.get(op.primitive_name)
        name   = plugin.display_name if plugin else op.primitive_name
        short  = "  ".join(f"{k}={v:.2g}" for k, v in list(op.params.items())[:2])
        self._lbl = QLabel(f"{name}  <span style='color:#607D8B'>{short}</span>")
        self._lbl.setTextFormat(Qt.TextFormat.RichText)
        self._lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._lbl.mousePressEvent = lambda _: self._select()
        row.addWidget(self._lbl)

        edit_btn = QToolButton()
        edit_btn.setText("⚙")
        edit_btn.setToolTip("Редактирай параметрите")
        edit_btn.setFixedSize(24, 24)
        edit_btn.clicked.connect(self._open_edit)
        row.addWidget(edit_btn)

        del_btn = QToolButton()
        del_btn.setText("✕")
        del_btn.setToolTip("Изтрий стъпката")
        del_btn.setFixedSize(24, 24)
        del_btn.clicked.connect(self._delete)
        row.addWidget(del_btn)

    # ------------------------------------------------------------------

    def highlight(self, active: bool) -> None:
        self._update_style(active)

    def _update_style(self, active: bool) -> None:
        bg     = "#2E3C43" if active else "#1E272E"
        border = "#4FC3F7" if active else "#37474F"
        self.setStyleSheet(
            f"#StepCard {{ background:{bg}; border:1px solid {border};"
            f" border-radius:3px; }}"
        )

    def _select(self) -> None:
        self.selected.emit(self._seq_idx, self._op_idx)

    def _toggle_enabled(self, state: int) -> None:
        self._op.enabled = bool(state)
        self._model._mutated(self._seq_idx, self._op_idx)

    def _open_edit(self) -> None:
        self._select()
        dlg = OperationEditDialog(
            self._model, self._seq_idx, self._op_idx, self._machine, self
        )
        dlg.exec()

    def _delete(self) -> None:
        seq = self._model.recipe.tool_sequences[self._seq_idx]
        seq.operations.pop(self._op_idx)
        new_oi = min(self._op_idx, len(seq.operations) - 1)
        self._model._mutated(self._seq_idx, new_oi)


# ---------------------------------------------------------------------------
# Sequence header
# ---------------------------------------------------------------------------

def _seq_header(seq: ToolSequence) -> QLabel:
    mode = "CSS" if seq.spindle_mode.value == "G96" else "G97"
    unit = "m/min" if mode == "CSS" else "rpm"
    lbl  = QLabel(f"T{seq.tool_id:02d}  ·  {mode} {seq.spindle_value:.0f} {unit}")
    font = lbl.font()
    font.setBold(True)
    font.setPointSize(font.pointSize() - 1)
    lbl.setFont(font)
    lbl.setStyleSheet(
        "color:#90A4AE; padding:6px 4px 2px 4px;"
        "border-bottom:1px solid #37474F;"
    )
    return lbl


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

class StepsPanel(QWidget):

    def __init__(
        self,
        model:   EditorModel,
        machine: Optional[MachineConfig] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._model   = model
        self._machine = machine
        self._cards: list[StepCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        root.addWidget(scroll)

        self._inner  = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        scroll.setWidget(self._inner)

        model.recipe_changed.connect(self._rebuild)
        model.selection_changed.connect(self._highlight)
        self._rebuild()

    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        self._cards.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for si, seq in enumerate(self._model.recipe.tool_sequences):
            self._layout.addWidget(_seq_header(seq))
            for oi, op in enumerate(seq.operations):
                card = StepCard(
                    self._model, si, oi, op, self._machine, self._inner
                )
                card.selected.connect(self._model.select)
                self._cards.append(card)
                self._layout.addWidget(card)

        self._layout.addStretch()
        self._highlight(self._model.selected_seq, self._model.selected_op)

    def _highlight(self, seq_idx: int, op_idx: int) -> None:
        for card in self._cards:
            active = (
                card._seq_idx == seq_idx
                and card._op_idx == op_idx
                and op_idx >= 0
            )
            card.highlight(active)
