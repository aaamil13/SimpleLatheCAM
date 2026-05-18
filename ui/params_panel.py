"""
ParamsPanel — auto-generated parameter editor for a LathePrimitive.

Reads LathePrimitive.params_schema and creates one row per ParamSpec:
  [label]  [QDoubleSpinBox]  [unit]

When any value changes the panel calls primitive.validate() and shows
an inline error message, then emits params_changed(dict).

The panel is replaced (not updated in-place) when a different primitive
is selected — call set_primitive() to swap it out.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext


class ParamsPanel(QWidget):
    """Emits params_changed(dict[str, float]) on every value change."""

    params_changed = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._primitive: Optional[LathePrimitive] = None
        self._context:   Optional[ProfileContext]  = None
        self._spinners:  dict[str, QDoubleSpinBox] = {}
        self._combos:    dict[str, QComboBox]      = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._title  = QLabel()
        self._title.setStyleSheet("font-weight: bold; padding: 4px 6px;")
        outer.addWidget(self._title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        self._form_widget = QWidget()
        self._form = QFormLayout(self._form_widget)
        self._form.setContentsMargins(6, 4, 6, 4)
        self._form.setSpacing(4)
        scroll.setWidget(self._form_widget)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #EF5350; padding: 4px 6px;")
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        outer.addWidget(self._error_label)

    # ------------------------------------------------------------------

    def set_primitive(
        self,
        primitive: Optional[LathePrimitive],
        params:    Optional[dict]       = None,
        context:   Optional[ProfileContext] = None,
    ) -> None:
        self._primitive = primitive
        self._context   = context
        self._rebuild(params)

    def set_context(self, context: Optional[ProfileContext]) -> None:
        self._context = context
        self._revalidate()

    # ------------------------------------------------------------------

    def _rebuild(self, params: Optional[dict]) -> None:
        self._spinners.clear()
        self._combos.clear()
        while self._form.rowCount():
            self._form.removeRow(0)

        if self._primitive is None:
            self._title.setText("")
            self._error_label.hide()
            return

        self._title.setText(self._primitive.display_name)
        current_params = params or self._primitive.default_params()

        for spec in self._primitive.params_schema:
            lbl = QLabel(spec.label)
            if spec.tooltip:
                lbl.setToolTip(spec.tooltip)

            if spec.choices is not None:
                cb = QComboBox()
                for ch in spec.choices:
                    cb.addItem(ch)
                idx = int(round(current_params.get(spec.name, spec.default)))
                cb.setCurrentIndex(max(0, min(idx, len(spec.choices) - 1)))
                if spec.tooltip:
                    cb.setToolTip(spec.tooltip)
                cb.currentIndexChanged.connect(self._on_value_changed)
                self._combos[spec.name] = cb
                self._form.addRow(lbl, cb)
            else:
                sb = QDoubleSpinBox()
                sb.setDecimals(3)
                sb.setSingleStep(spec.step)
                sb.setRange(spec.min_val, spec.max_val)
                sb.setValue(current_params.get(spec.name, spec.default))
                if spec.unit:
                    sb.setSuffix(f"  {spec.unit}")
                if spec.tooltip:
                    sb.setToolTip(spec.tooltip)
                sb.valueChanged.connect(self._on_value_changed)
                self._spinners[spec.name] = sb
                self._form.addRow(lbl, sb)

        self._revalidate()

    def _on_value_changed(self) -> None:
        changed = self._sender_name()
        params  = self._current_params()
        if changed and self._primitive is not None:
            updated = self._primitive.on_param_changed(changed, params)
            if updated is not params:
                self._apply_params(updated)
        self._revalidate()
        self.params_changed.emit(self._current_params())

    def _sender_name(self) -> str | None:
        s = self.sender()
        for name, w in self._spinners.items():
            if w is s:
                return name
        for name, w in self._combos.items():
            if w is s:
                return name
        return None

    def _apply_params(self, params: dict) -> None:
        """Push new values into widgets without re-triggering _on_value_changed."""
        for name, sb in self._spinners.items():
            if name in params:
                sb.blockSignals(True)
                sb.setValue(params[name])
                sb.blockSignals(False)
        for name, cb in self._combos.items():
            if name in params:
                cb.blockSignals(True)
                cb.setCurrentIndex(int(round(params[name])))
                cb.blockSignals(False)

    def _current_params(self) -> dict:
        params = {name: sb.value() for name, sb in self._spinners.items()}
        params.update({name: float(cb.currentIndex()) for name, cb in self._combos.items()})
        return params

    def _revalidate(self) -> None:
        if self._primitive is None:
            self._error_label.hide()
            return
        ctx = self._context or ProfileContext(
            cursor_x=0.0, cursor_z=0.0,
            stock_d=1000.0, stock_l=1000.0,
            segment_count=self._primitive.min_segments,
        )
        err = self._primitive.validate(self._current_params(), ctx)
        if err:
            self._error_label.setText(err)
            self._error_label.show()
        else:
            self._error_label.hide()
