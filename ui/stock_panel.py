"""
StockPanel — collapsible group box for configuring the raw stock.

Placed at the top of StepsPanel so the operator sets the billet
dimensions and material before adding machining operations.

Connects to EditorModel.update_stock() for live CAM recalculation.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
)

from ui.editor_model import EditorModel


class StockPanel(QGroupBox):

    def __init__(self, model: EditorModel, parent=None) -> None:
        super().__init__("Заготовка", parent)
        self._model     = model
        self._refreshing = False

        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #4FC3F7;
                border-radius: 4px;
                margin-top: 10px;
                background-color: #263238;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #4FC3F7;
            }
        """)

        layout = QFormLayout(self)
        layout.setContentsMargins(10, 16, 10, 10)
        layout.setSpacing(6)

        self._spin_d = QDoubleSpinBox()
        self._spin_d.setRange(1.0, 1000.0)
        self._spin_d.setDecimals(1)
        self._spin_d.setSuffix(" mm")
        self._spin_d.setSingleStep(1.0)
        layout.addRow("Диаметър:", self._spin_d)

        self._spin_l = QDoubleSpinBox()
        self._spin_l.setRange(1.0, 3000.0)
        self._spin_l.setDecimals(1)
        self._spin_l.setSuffix(" mm")
        self._spin_l.setSingleStep(5.0)
        layout.addRow("Дължина:", self._spin_l)

        self._combo_mat = QComboBox()
        for mat in model.material_library.all():
            self._combo_mat.addItem(mat.name, mat.key)
        layout.addRow("Материал:", self._combo_mat)

        self._refresh_from_model()

        self._spin_d.valueChanged.connect(self._on_change)
        self._spin_l.valueChanged.connect(self._on_change)
        self._combo_mat.currentIndexChanged.connect(self._on_change)
        model.recipe_changed.connect(self._refresh_from_model)

    # ------------------------------------------------------------------

    def _refresh_from_model(self) -> None:
        """Sync spinners with the current recipe — blocks feedback loop."""
        self._refreshing = True
        stock = self._model.recipe.stock
        self._spin_d.setValue(stock.diameter)
        self._spin_l.setValue(stock.length)
        idx = self._combo_mat.findData(stock.material_key)
        if idx >= 0:
            self._combo_mat.setCurrentIndex(idx)
        self._refreshing = False

    def _on_change(self) -> None:
        if self._refreshing:
            return
        self._model.update_stock(
            diameter=self._spin_d.value(),
            length=self._spin_l.value(),
            material_key=self._combo_mat.currentData() or "",
        )
