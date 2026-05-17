"""
PartRecipe — complete parametric description of a turned part.

A recipe is the single source of truth that the editor saves and reloads.
It stores everything needed to:
  - Rebuild the LatheProfile (geometry)
  - Generate G-code (tools, spindle mode, cutting data)
  - Restore the UI (operation tree, parameter panels)

Structure
---------
  PartRecipe
  └── stock  (diameter, length, material key)
  └── tool_sequences : list[ToolSequence]   (ordered)
      └── tool_id, spindle_mode, spindle_value
      └── operations : list[OperationRecord]  (ordered)
          └── primitive_name, params, direction

JSON round-trip is the only persistence format.  No binary formats.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from domain.tool import SpindleMode, ToolDirection


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------

@dataclass
class StockSpec:
    diameter:     float   # mm — outer diameter of the raw bar/billet
    length:       float   # mm — total length of the raw stock
    material_key: str     = "steel_45"


# ---------------------------------------------------------------------------
# OperationRecord — one primitive applied to the profile
# ---------------------------------------------------------------------------

@dataclass
class OperationRecord:
    """
    Serialisable record of a single primitive operation.

    primitive_name  : matches LathePrimitive.name (plug-in key)
    params          : dict of parameter values (matches params_schema)
    direction       : EXTERNAL or INTERNAL  (used by CAM engine)
    enabled         : False → operation is skipped during G-code generation
                      (allows temporary disabling without deleting)
    """
    primitive_name: str
    params:         dict[str, float]    = field(default_factory=dict)
    direction:      ToolDirection       = ToolDirection.EXTERNAL
    enabled:        bool                = True
    coolant_on:     Optional[bool]      = None  # None = inherit from ToolSequence


# ---------------------------------------------------------------------------
# ToolSequence — group of operations executed with one tool
# ---------------------------------------------------------------------------

@dataclass
class ToolSequence:
    """
    All operations performed before the next tool change.

    tool_id       : matches Tool.tool_id in ToolLibrary
    spindle_mode  : G97 (constant RPM) or G96 (CSS)
    spindle_value : RPM for G97; surface speed m/min for G96
    max_rpm       : upper RPM limit when G96 CSS mode is active
    coolant_on    : M8 before operations, M9 after
    operations    : ordered list of OperationRecords
    """
    tool_id:       int
    spindle_mode:  SpindleMode   = SpindleMode.CSS
    spindle_value: float         = 200.0     # m/min for CSS, RPM for G97
    max_rpm:       int           = 2500
    coolant_on:    bool          = True
    operations:    list[OperationRecord] = field(default_factory=list)

    def add(self, op: OperationRecord) -> None:
        self.operations.append(op)

    def remove(self, index: int) -> None:
        del self.operations[index]

    def move(self, from_idx: int, to_idx: int) -> None:
        """Reorder an operation within the sequence."""
        op = self.operations.pop(from_idx)
        self.operations.insert(to_idx, op)

    @property
    def enabled_operations(self) -> list[OperationRecord]:
        return [op for op in self.operations if op.enabled]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _op_to_dict(op: "OperationRecord") -> dict:
    d: dict = {
        "primitive": op.primitive_name,
        "params":    op.params,
        "direction": op.direction.value,
        "enabled":   op.enabled,
    }
    if op.coolant_on is not None:
        d["coolant_on"] = op.coolant_on
    return d


# ---------------------------------------------------------------------------
# PartRecipe
# ---------------------------------------------------------------------------

@dataclass
class PartRecipe:
    """
    Complete parametric recipe for a turned part.

    part_name       : free-text identifier shown in the editor title
    stock           : raw material dimensions and material key
    tool_sequences  : ordered list; each entry triggers one tool change
    notes           : operator notes (shown in G-code header comment)
    """
    part_name:      str                  = "Untitled Part"
    stock:          StockSpec            = field(default_factory=lambda: StockSpec(50.0, 100.0))
    tool_sequences: list[ToolSequence]   = field(default_factory=list)
    notes:          str                  = ""

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def add_sequence(self, seq: ToolSequence) -> None:
        self.tool_sequences.append(seq)

    def remove_sequence(self, index: int) -> None:
        del self.tool_sequences[index]

    def all_tool_ids(self) -> list[int]:
        """Unique tool IDs referenced by this recipe, in appearance order."""
        seen: list[int] = []
        for seq in self.tool_sequences:
            if seq.tool_id not in seen:
                seen.append(seq.tool_id)
        return seen

    def all_operations(self) -> list[tuple[int, ToolSequence, OperationRecord]]:
        """Flat iterator: (global_index, sequence, operation_record)."""
        idx = 0
        result = []
        for seq in self.tool_sequences:
            for op in seq.operations:
                result.append((idx, seq, op))
                idx += 1
        return result

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path | str) -> "PartRecipe":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls._from_dict(data)

    @classmethod
    def default(cls, stock_d: float = 50.0, stock_l: float = 150.0) -> "PartRecipe":
        """Empty recipe with one default ToolSequence — ready for first operation."""
        return cls(
            part_name="New Part",
            stock=StockSpec(diameter=stock_d, length=stock_l),
            tool_sequences=[
                ToolSequence(
                    tool_id=1,
                    spindle_mode=SpindleMode.CSS,
                    spindle_value=200.0,
                    max_rpm=2500,
                    coolant_on=True,
                )
            ],
        )

    # ------------------------------------------------------------------
    # Dict helpers (also used by the UI for copy/paste)
    # ------------------------------------------------------------------

    def _to_dict(self) -> dict:
        return {
            "part_name": self.part_name,
            "notes":     self.notes,
            "stock": {
                "diameter":     self.stock.diameter,
                "length":       self.stock.length,
                "material_key": self.stock.material_key,
            },
            "tool_sequences": [
                {
                    "tool_id":       seq.tool_id,
                    "spindle_mode":  seq.spindle_mode.value,
                    "spindle_value": seq.spindle_value,
                    "max_rpm":       seq.max_rpm,
                    "coolant_on":    seq.coolant_on,
                    "operations": [
                        _op_to_dict(op)
                        for op in seq.operations
                    ],
                }
                for seq in self.tool_sequences
            ],
        }

    @classmethod
    def _from_dict(cls, d: dict) -> "PartRecipe":
        s = d.get("stock", {})
        stock = StockSpec(
            diameter=s.get("diameter", 50.0),
            length=s.get("length", 100.0),
            material_key=s.get("material_key", "steel_45"),
        )
        sequences = []
        for sd in d.get("tool_sequences", []):
            ops = [
                OperationRecord(
                    primitive_name=od["primitive"],
                    params=od.get("params", {}),
                    direction=ToolDirection(od.get("direction", "external")),
                    enabled=od.get("enabled", True),
                    coolant_on=od.get("coolant_on", None),
                )
                for od in sd.get("operations", [])
            ]
            sequences.append(ToolSequence(
                tool_id=sd["tool_id"],
                spindle_mode=SpindleMode(sd.get("spindle_mode", "G96")),
                spindle_value=sd.get("spindle_value", 200.0),
                max_rpm=sd.get("max_rpm", 2500),
                coolant_on=sd.get("coolant_on", True),
                operations=ops,
            ))
        return cls(
            part_name=d.get("part_name", "Untitled Part"),
            notes=d.get("notes", ""),
            stock=stock,
            tool_sequences=sequences,
        )
