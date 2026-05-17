"""
Tool model — ISO 1832 insert + holder + per-material cutting data.

ToolInsert   — geometry of the indexable insert (shape, angle, nose radius)
ToolHolder   — geometry of the holder (approach angle, hand, direction)
CuttingData  — recommended and maximum Vc / fn / ap per material key
Tool         — insert + holder + id + cutting_data dict
SpindleMode  — G96 (CSS) or G97 (constant RPM) enum

Serialisation lives in tool_library.py to keep this file under 300 lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class InsertShape(str, Enum):
    """ISO 1832 position 1 — insert shape and included angle."""
    C = "C"   # 80° rhombus
    D = "D"   # 55° rhombus
    K = "K"   # 55° parallelogram
    R = "R"   # round
    S = "S"   # square (90°)
    T = "T"   # triangle (60°)
    V = "V"   # 35° rhombus (finishing)
    W = "W"   # trigon 80°

    @property
    def included_angle(self) -> float:
        """Nominal included angle of the cutting edge in degrees."""
        return {
            "C": 80.0, "D": 55.0, "K": 55.0, "R": 360.0,
            "S": 90.0, "T": 60.0, "V": 35.0,  "W": 80.0,
        }[self.value]


class InsertClearance(str, Enum):
    """ISO 1832 position 2 — relief / clearance angle."""
    N = "N"   # 0°
    A = "A"   # 3°
    B = "B"   # 5°
    C = "C"   # 7°
    P = "P"   # 11°

    @property
    def angle_deg(self) -> float:
        return {"N": 0.0, "A": 3.0, "B": 5.0, "C": 7.0, "P": 11.0}[self.value]


class ToolHand(str, Enum):
    """Holder hand (cutting direction)."""
    R = "R"   # right-hand — cuts toward chuck
    L = "L"   # left-hand  — cuts away from chuck
    N = "N"   # neutral


class ToolDirection(str, Enum):
    """Whether the tool operates on an external or internal surface."""
    EXTERNAL = "external"
    INTERNAL = "internal"


class SpindleMode(str, Enum):
    """G97 = constant RPM, G96 = constant surface speed (CSS)."""
    CONSTANT_RPM = "G97"
    CSS          = "G96"


# ---------------------------------------------------------------------------
# Insert geometry
# ---------------------------------------------------------------------------

@dataclass
class ToolInsert:
    """Geometric description of an indexable turning insert."""
    shape:        InsertShape     = InsertShape.C
    clearance:    InsertClearance = InsertClearance.N
    nose_radius:  float           = 0.4     # mm — Rε, used by Clipper offset
    ic_size:      float           = 12.7    # mm — inscribed circle diameter
    thickness:    float           = 4.76    # mm

    # Optional free-text fields for catalogue reference
    manufacturer: str = ""
    iso_code:     str = ""       # e.g. "CNMG 120408"

    @property
    def cutting_angle(self) -> float:
        """Included angle of the insert in degrees."""
        return self.shape.included_angle


# ---------------------------------------------------------------------------
# Holder geometry
# ---------------------------------------------------------------------------

@dataclass
class ToolHolder:
    """Geometric description of the tool holder / shank."""
    approach_angle: float        = 95.0          # κr — lead angle (degrees)
    hand:           ToolHand     = ToolHand.R
    direction:      ToolDirection = ToolDirection.EXTERNAL
    shank_w:        float        = 25.0          # mm
    shank_h:        float        = 25.0          # mm

    manufacturer: str = ""
    iso_code:     str = ""       # e.g. "PCLNR 2525M12"


# ---------------------------------------------------------------------------
# Cutting data per material
# ---------------------------------------------------------------------------

@dataclass
class CuttingData:
    """
    Recommended and maximum cutting parameters for one material.

    vc_rec / vc_max  — surface speed   (m/min)
    fn_rec / fn_max  — feed per rev    (mm/rev)
    ap_rec / ap_max  — depth of cut    (mm)
    """
    material_key: str    # must match a key in MaterialLibrary

    vc_rec:  float = 200.0
    vc_max:  float = 280.0
    fn_rec:  float = 0.20
    fn_max:  float = 0.40
    ap_rec:  float = 2.0
    ap_max:  float = 4.0

    def rpm_for_diameter(self, diameter_mm: float) -> float:
        """Compute spindle RPM for recommended Vc at the given diameter."""
        if diameter_mm <= 0:
            return 0.0
        return (self.vc_rec * 1000.0) / (math.pi * diameter_mm)

    def rpm_max_for_diameter(self, diameter_mm: float) -> float:
        """Compute spindle RPM for maximum Vc at the given diameter."""
        if diameter_mm <= 0:
            return 0.0
        return (self.vc_max * 1000.0) / (math.pi * diameter_mm)


# lazy import to avoid circular reference in rpm helpers
import math   # noqa: E402  (placed after dataclass definitions intentionally)


# ---------------------------------------------------------------------------
# Tool — composite of insert + holder + cutting data
# ---------------------------------------------------------------------------

@dataclass
class Tool:
    """
    A complete lathe tool entry: insert, holder, LinuxCNC tool-table id,
    and per-material cutting data.
    """
    tool_id:      int
    insert:       ToolInsert       = field(default_factory=ToolInsert)
    holder:       ToolHolder       = field(default_factory=ToolHolder)
    cutting_data: dict[str, CuttingData] = field(default_factory=dict)
    description:  str              = ""

    @property
    def nose_radius(self) -> float:
        """Shortcut to insert.nose_radius — used by Clipper offset."""
        return self.insert.nose_radius

    @property
    def direction(self) -> ToolDirection:
        """Shortcut to holder.direction."""
        return self.holder.direction

    def data_for(self, material_key: str) -> CuttingData | None:
        """Return CuttingData for *material_key*, or None if not defined."""
        return self.cutting_data.get(material_key)

    def best_data(self, material_key: str) -> CuttingData:
        """Return CuttingData for *material_key*, falling back to first
        available entry, then to a generic default."""
        if material_key in self.cutting_data:
            return self.cutting_data[material_key]
        if self.cutting_data:
            return next(iter(self.cutting_data.values()))
        return CuttingData(material_key=material_key)   # generic fallback
