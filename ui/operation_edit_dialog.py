"""
OperationEditDialog — modal dialog for editing a single operation's parameters.

Contains:
  - ParamsPanel for numeric inputs
  - MessageEditor for operator_message primitives
  - Coolant override checkbox (when machine has coolant)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QVBoxLayout,
    QWidget,
)

from domain.app_config import AppConfig
from domain.machine import MachineConfig
from ui.editor_model import EditorModel
from ui.message_editor import MessageEditor
from ui.params_panel import ParamsPanel


class OperationEditDialog(QDialog):
    """Modal dialog: ParamsPanel + optional MessageEditor + coolant toggle."""

    def __init__(
        self,
        model:      EditorModel,
        seq_idx:    int,
        op_idx:     int,
        machine:    Optional[MachineConfig] = None,
        app_config: Optional[AppConfig]    = None,
        parent:     Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._model   = model
        self._seq_idx = seq_idx
        self._op_idx  = op_idx

        seq    = model.recipe.tool_sequences[seq_idx]
        op     = seq.operations[op_idx]
        plugin = model.loader.get(op.primitive_name)
        lang   = app_config.operator_language if app_config else "bg"

        self.setWindowTitle(plugin.display_name if plugin else op.primitive_name)
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._panel = ParamsPanel(self)
        ctx = model.profile.context()
        self._panel.set_primitive(plugin, op.params, ctx)
        self._panel.params_changed.connect(self._on_params_changed)
        layout.addWidget(self._panel)

        if op.primitive_name == "operator_message":
            self._msg_editor = MessageEditor(op.extras, primary_lang=lang, parent=self)
            self._msg_editor.extras_changed.connect(self._on_extras_changed)
            layout.addWidget(self._msg_editor)

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

    def _on_extras_changed(self, extras: dict) -> None:
        op = self._model.recipe.tool_sequences[self._seq_idx].operations[self._op_idx]
        op.extras = {k: v for k, v in extras.items() if v}
        self._model._mutated(self._seq_idx, self._op_idx)

    def _on_coolant_changed(self, state: int) -> None:
        self._model.select(self._seq_idx, self._op_idx)
        self._model.update_coolant_override(bool(state))
