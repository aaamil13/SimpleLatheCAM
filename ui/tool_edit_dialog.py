"""
ToolEditDialog — modal dialog for creating / editing a single Tool entry.

Tabs
----
  Вложка       — InsertShape, InsertClearance, nose_radius, ic_size, iso_code
  Държач       — approach_angle, hand, direction, shank dimensions, iso_code
  Режими       — QTableWidget: one row per material, columns Vc/fn/ap rec+max

Call get_tool() after exec() to retrieve the edited Tool dataclass.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QComboBox,
    QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from domain.material import MaterialLibrary
from domain.tool import (
    CuttingData, InsertClearance, InsertShape,
    Tool, ToolDirection, ToolHand, ToolHolder, ToolInsert,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dspin(lo: float, hi: float, dec: int, step: float, suffix: str = "") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setSingleStep(step)
    if suffix:
        s.setSuffix(suffix)
    return s


def _combo(items: list[str]) -> QComboBox:
    c = QComboBox()
    for i in items:
        c.addItem(i)
    return c


# ---------------------------------------------------------------------------
# Individual tabs
# ---------------------------------------------------------------------------

class _InsertTab(QWidget):
    def __init__(self, insert: ToolInsert, parent=None) -> None:
        super().__init__(parent)
        lay = QFormLayout(self)
        lay.setSpacing(8)

        self._shape     = _combo([s.value for s in InsertShape])
        self._clearance = _combo([c.value for c in InsertClearance])
        self._nose_r    = _dspin(0.01, 10.0, 2, 0.05, " mm")
        self._ic        = _dspin(1.0, 50.0, 2, 0.5, " mm")
        self._thick     = _dspin(1.0, 20.0, 2, 0.5, " mm")
        self._iso       = QLineEdit()
        self._mfr       = QLineEdit()

        lay.addRow("Форма (ISO):",      self._shape)
        lay.addRow("Ъгъл на освобождаване:", self._clearance)
        lay.addRow("Нос-радиус (Rε):", self._nose_r)
        lay.addRow("Вписан ∅ (IC):",   self._ic)
        lay.addRow("Дебелина:",         self._thick)
        lay.addRow("ISO код:",          self._iso)
        lay.addRow("Производител:",     self._mfr)

        self._shape.setCurrentText(insert.shape.value)
        self._clearance.setCurrentText(insert.clearance.value)
        self._nose_r.setValue(insert.nose_radius)
        self._ic.setValue(insert.ic_size)
        self._thick.setValue(insert.thickness)
        self._iso.setText(insert.iso_code)
        self._mfr.setText(insert.manufacturer)

    def get_insert(self) -> ToolInsert:
        return ToolInsert(
            shape=InsertShape(self._shape.currentText()),
            clearance=InsertClearance(self._clearance.currentText()),
            nose_radius=self._nose_r.value(),
            ic_size=self._ic.value(),
            thickness=self._thick.value(),
            iso_code=self._iso.text().strip(),
            manufacturer=self._mfr.text().strip(),
        )


class _HolderTab(QWidget):
    def __init__(self, holder: ToolHolder, parent=None) -> None:
        super().__init__(parent)
        lay = QFormLayout(self)
        lay.setSpacing(8)

        self._angle  = _dspin(1.0, 179.0, 1, 1.0, "°")
        self._hand   = _combo([h.value for h in ToolHand])
        self._dir    = _combo([d.value for d in ToolDirection])
        self._sw     = _dspin(5.0, 100.0, 1, 1.0, " mm")
        self._sh     = _dspin(5.0, 100.0, 1, 1.0, " mm")
        self._iso    = QLineEdit()
        self._mfr    = QLineEdit()

        lay.addRow("Подходящ ъгъл (κr):", self._angle)
        lay.addRow("Ръка:",               self._hand)
        lay.addRow("Посока:",             self._dir)
        lay.addRow("Ширина на шанк:",     self._sw)
        lay.addRow("Височина на шанк:",   self._sh)
        lay.addRow("ISO код:",            self._iso)
        lay.addRow("Производител:",       self._mfr)

        self._angle.setValue(holder.approach_angle)
        self._hand.setCurrentText(holder.hand.value)
        self._dir.setCurrentText(holder.direction.value)
        self._sw.setValue(holder.shank_w)
        self._sh.setValue(holder.shank_h)
        self._iso.setText(holder.iso_code)
        self._mfr.setText(holder.manufacturer)

    def get_holder(self) -> ToolHolder:
        return ToolHolder(
            approach_angle=self._angle.value(),
            hand=ToolHand(self._hand.currentText()),
            direction=ToolDirection(self._dir.currentText()),
            shank_w=self._sw.value(),
            shank_h=self._sh.value(),
            iso_code=self._iso.text().strip(),
            manufacturer=self._mfr.text().strip(),
        )


_CD_COLS = ["Vc rec", "Vc max", "fn rec", "fn max", "ap rec", "ap max"]
_CD_UNITS = ["m/min", "m/min", "mm/rev", "mm/rev", "mm", "mm"]
_CD_RANGES = [(1, 2000), (1, 2000), (0.01, 5.0), (0.01, 5.0), (0.01, 50.0), (0.01, 50.0)]
_CD_DECS   = [0, 0, 3, 3, 2, 2]


class _CuttingTab(QWidget):
    def __init__(
        self,
        cutting_data: dict[str, CuttingData],
        material_library: MaterialLibrary,
        parent=None,
    ) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)

        mats = list(material_library.all())
        headers = ["Материал"] + [f"{c}\n{u}" for c, u in zip(_CD_COLS, _CD_UNITS)]
        self._table = QTableWidget(len(mats), len(headers), self)
        self._table.setHorizontalHeaderLabels(headers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        for col in range(1, len(headers)):
            self._table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.Stretch
            )

        self._mat_keys: list[str] = []
        self._spins: list[list[QDoubleSpinBox]] = []

        for row, mat in enumerate(mats):
            self._mat_keys.append(mat.key)
            lbl = QTableWidgetItem(mat.name)
            lbl.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(row, 0, lbl)

            cd = cutting_data.get(mat.key) or CuttingData(material_key=mat.key)
            vals = [cd.vc_rec, cd.vc_max, cd.fn_rec, cd.fn_max, cd.ap_rec, cd.ap_max]
            row_spins: list[QDoubleSpinBox] = []
            for col_i, (val, (lo, hi), dec) in enumerate(
                zip(vals, _CD_RANGES, _CD_DECS), start=1
            ):
                sp = QDoubleSpinBox()
                sp.setRange(lo, hi)
                sp.setDecimals(dec)
                sp.setValue(val)
                sp.setFrame(False)
                self._table.setCellWidget(row, col_i, sp)
                row_spins.append(sp)
            self._spins.append(row_spins)

        lay.addWidget(self._table)

    def get_cutting_data(self) -> dict[str, CuttingData]:
        result: dict[str, CuttingData] = {}
        for row, key in enumerate(self._mat_keys):
            sp = self._spins[row]
            result[key] = CuttingData(
                material_key=key,
                vc_rec=sp[0].value(), vc_max=sp[1].value(),
                fn_rec=sp[2].value(), fn_max=sp[3].value(),
                ap_rec=sp[4].value(), ap_max=sp[5].value(),
            )
        return result


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class ToolEditDialog(QDialog):
    """Edit one Tool — id, description, insert, holder, cutting data."""

    def __init__(
        self,
        tool: Tool,
        material_library: MaterialLibrary,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактиране на инструмент")
        self.setMinimumSize(540, 480)
        self._tool = deepcopy(tool)

        root = QVBoxLayout(self)

        # Top row: Tool ID + description
        top = QHBoxLayout()
        top.addWidget(QLabel("T#:"))
        self._id_spin = QSpinBox()
        self._id_spin.setRange(1, 99)
        self._id_spin.setValue(tool.tool_id)
        top.addWidget(self._id_spin)
        top.addSpacing(12)
        top.addWidget(QLabel("Описание:"))
        self._desc = QLineEdit(tool.description)
        top.addWidget(self._desc, 1)
        root.addLayout(top)

        # Tabs
        tabs = QTabWidget()
        self._insert_tab  = _InsertTab(tool.insert, self)
        self._holder_tab  = _HolderTab(tool.holder, self)
        self._cutting_tab = _CuttingTab(tool.cutting_data, material_library, self)
        tabs.addTab(self._insert_tab,  "Вложка")
        tabs.addTab(self._holder_tab,  "Държач")
        tabs.addTab(self._cutting_tab, "Режими на рязане")
        root.addWidget(tabs)

        # Buttons
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def get_tool(self) -> Tool:
        """Return the edited Tool. Call after exec() == Accepted."""
        return Tool(
            tool_id=self._id_spin.value(),
            description=self._desc.text().strip(),
            insert=self._insert_tab.get_insert(),
            holder=self._holder_tab.get_holder(),
            cutting_data=self._cutting_tab.get_cutting_data(),
        )
