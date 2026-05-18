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
    QFrame,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from domain.app_config import AppConfig
from domain.machine import MachineConfig
from domain.recipe import OperationRecord, ToolSequence
from domain.profile import LatheProfile
from ui.editor_model import EditorModel
from ui.mini_canvas import MiniProfileView
from ui.operation_edit_dialog import OperationEditDialog
from ui.stock_panel import StockEditDialog


# ---------------------------------------------------------------------------
# Stock card — always first in the list
# ---------------------------------------------------------------------------

class StockCard(QFrame):
    """Compact card showing raw stock dimensions; ⚙ opens StockEditDialog."""

    def __init__(self, model: EditorModel, parent=None) -> None:
        super().__init__(parent)
        self._model = model
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("StockCard")
        self.setStyleSheet(
            "#StockCard { background:#1E272E; border:1.5px solid #FFB74D;"
            " border-radius:3px; }"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 4, 3)
        outer.setSpacing(2)

        row = QHBoxLayout()
        row.setSpacing(4)
        self._lbl = QLabel()
        self._lbl.setTextFormat(Qt.TextFormat.RichText)
        self._lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(self._lbl)

        btn = QToolButton()
        btn.setText("⚙")
        btn.setToolTip("Настройка на заготовката")
        btn.setFixedSize(24, 24)
        btn.clicked.connect(self._open_edit)
        row.addWidget(btn)
        outer.addLayout(row)

        self._mini = MiniProfileView(self)
        outer.addWidget(self._mini)

        self._refresh()
        model.recipe_changed.connect(self._refresh)

    def _refresh(self) -> None:
        s = self._model.recipe.stock
        self._lbl.setText(
            f"<b>Заготовка</b>  "
            f"<span style='color:#FFB74D'>⌀{s.diameter:.1f} × {s.length:.1f} mm</span>"
        )
        blank = LatheProfile(stock_d=s.diameter, stock_l=s.length)
        self._mini.set_profile(blank)

    def _open_edit(self) -> None:
        StockEditDialog(self._model, self).exec()


# ---------------------------------------------------------------------------
# Single step card
# ---------------------------------------------------------------------------

class StepCard(QFrame):
    selected = Signal(int, int)

    def __init__(
        self,
        model:      EditorModel,
        seq_idx:    int,
        op_idx:     int,
        op:         OperationRecord,
        machine:    Optional[MachineConfig] = None,
        app_config: Optional[AppConfig]    = None,
        parent:     Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._model      = model
        self._seq_idx    = seq_idx
        self._op_idx     = op_idx
        self._op         = op
        self._machine    = machine
        self._app_config = app_config

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("StepCard")
        self._update_style(False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 3, 4, 2)
        outer.setSpacing(2)

        row = QHBoxLayout()
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

        outer.addLayout(row)
        self._mini = MiniProfileView(self)
        self._mini.set_profile(model.get_profile_up_to(seq_idx, op_idx))
        outer.addWidget(self._mini)

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
            self._model, self._seq_idx, self._op_idx,
            self._machine, self._app_config, self
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
        model:      EditorModel,
        machine:    Optional[MachineConfig] = None,
        app_config: Optional[AppConfig]    = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._model      = model
        self._machine    = machine
        self._app_config = app_config
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

        # StockCard is permanent — kept across rebuilds
        self._stock_card = StockCard(model, self._inner)

        model.recipe_changed.connect(self._rebuild)
        model.selection_changed.connect(self._highlight)
        self._rebuild()

    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        self._cards.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w and w is not self._stock_card:
                w.deleteLater()

        self._layout.addWidget(self._stock_card)
        for si, seq in enumerate(self._model.recipe.tool_sequences):
            self._layout.addWidget(_seq_header(seq))
            for oi, op in enumerate(seq.operations):
                card = StepCard(
                    self._model, si, oi, op,
                    self._machine, self._app_config, self._inner
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
