"""
MachineConfig — geometry, limits, and safe positions of the lathe.

Loaded from a JSON file at startup.  All CAM and UI components that need to
know machine boundaries (travel limits, safe rapid positions, spindle max)
receive a MachineConfig instance rather than hard-coded constants.

Roles in the system
-------------------
  Validation   : ProfileContext is extended with machine limits so plug-ins
                 can warn when a feature would exceed travel.
  GCodeWriter  : uses safe_positions to generate approach/retract rapids and
                 the tool-change position; uses max_spindle_rpm to cap G96 CSS.
  Canvas 2D    : draws soft-limit guides and safe-position markers.
  RapidTo plug : validates target coordinates against axis limits.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class ChuckSide(str, Enum):
    """Which side of the bed the spindle/chuck is mounted on.

    LEFT  — standard configuration: chuck on the operator's left,
            tailstock on the right.  Z decreases left-to-right.
    RIGHT — reversed spindle (e.g. sub-spindle or inverted lathe):
            chuck on the right, tailstock on the left.
            The canvas mirrors the Z axis for correct visualisation.
    """
    LEFT  = "left"
    RIGHT = "right"


# ---------------------------------------------------------------------------
# Sub-structures
# ---------------------------------------------------------------------------

@dataclass
class AxisLimits:
    """
    Software travel limits for each axis (mm).

    Convention (lathe):
      X — radial axis.  x_min is typically 0 (centreline) or slightly
          negative (for facing past centre).  x_max is the largest
          diameter the machine can reach.
      Z — axial axis.  z_max is typically 0 (face of chuck / datum).
          z_min is the furthest position away from the chuck (negative).
    """
    x_min: float = 0.0
    x_max: float = 150.0    # radius — diameter capacity 300 mm
    z_min: float = -400.0   # max distance from chuck
    z_max: float = 5.0      # small positive clearance beyond face datum

    def contains(self, x_radius: float, z: float) -> bool:
        """True if the point (x_radius, z) is within soft limits."""
        return (
            self.x_min <= x_radius <= self.x_max
            and self.z_min <= z <= self.z_max
        )

    def clamp_x(self, x_radius: float) -> float:
        return max(self.x_min, min(self.x_max, x_radius))

    def clamp_z(self, z: float) -> float:
        return max(self.z_min, min(self.z_max, z))

    def check(self, x_radius: float, z: float) -> str | None:
        """Return an error string if the point is out of limits, else None."""
        errors = []
        if x_radius < self.x_min or x_radius > self.x_max:
            errors.append(
                f"X radius {x_radius:.3f} mm outside limits "
                f"[{self.x_min}, {self.x_max}]"
            )
        if z < self.z_min or z > self.z_max:
            errors.append(
                f"Z {z:.3f} mm outside limits [{self.z_min}, {self.z_max}]"
            )
        return "; ".join(errors) if errors else None


@dataclass
class SafePositions:
    """
    Named positions used by the GCodeWriter for rapids and tool changes.

    All X values are *radii* (half-diameter), matching the internal convention
    of LatheProfile.  The GCodeWriter converts to diameter for G-code output
    (diameter programming is the default for lathes).
    """
    # Clearance above the stock for rapid traverses during roughing
    x_clearance: float = 5.0      # radius, added on top of stock radius

    # Position the machine moves to before a tool change
    x_tool_change: float = 100.0  # radius (well away from the part)
    z_tool_change: float = 50.0   # positive — behind the face datum

    # Home / end-of-program position
    x_home: float = 100.0
    z_home: float = 50.0

    # Z approach distance before the first pass (clearance in front of stock face)
    z_approach_clearance: float = 2.0


# ---------------------------------------------------------------------------
# Main configuration class
# ---------------------------------------------------------------------------

@dataclass
class MachineConfig:
    """
    Complete geometric and operational configuration of the lathe.

    Reasonable defaults are provided so the software runs without a config
    file (useful for development on a non-CNC workstation).
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name: str = "Lathe"
    description: str = ""

    # ------------------------------------------------------------------
    # Spindle
    # ------------------------------------------------------------------
    max_spindle_rpm: int = 3000
    min_spindle_rpm: int = 50

    # ------------------------------------------------------------------
    # Axes
    # ------------------------------------------------------------------
    limits: AxisLimits = field(default_factory=AxisLimits)
    safe: SafePositions = field(default_factory=SafePositions)

    # Rapid feed rates (mm/min).  0 = machine default (G00 uses machine max).
    x_rapid_mmpm: float = 0.0
    z_rapid_mmpm: float = 0.0

    # ------------------------------------------------------------------
    # Workholding geometry
    # ------------------------------------------------------------------
    chuck_side: ChuckSide = ChuckSide.LEFT   # spindle position on the bed
    chuck_diameter: float = 200.0            # mm — used for collision preview
    chuck_jaw_depth: float = 40.0            # mm — axial depth of the chuck jaws
    bar_capacity: float = 52.0               # mm diameter — through-bar bore

    # ------------------------------------------------------------------
    # Extras
    # ------------------------------------------------------------------
    coolant_available: bool = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def approach_x_radius(self, stock_d: float) -> float:
        """
        Safe X radius for rapid approach: stock radius + clearance.
        Used by GCodeWriter before each roughing pass.
        """
        return stock_d / 2.0 + self.safe.x_clearance

    def cap_rpm(self, requested_rpm: float) -> int:
        """Clamp a computed RPM value to the machine's spindle range."""
        return int(max(self.min_spindle_rpm, min(self.max_spindle_rpm, requested_rpm)))

    def validate_position(self, x_radius: float, z: float) -> str | None:
        """Delegate to AxisLimits.check(); returns error string or None."""
        return self.limits.check(x_radius, z)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "description": self.description,
            "spindle": {
                "max_rpm": self.max_spindle_rpm,
                "min_rpm": self.min_spindle_rpm,
            },
            "axes": {
                "limits": asdict(self.limits),
                "x_rapid_mmpm": self.x_rapid_mmpm,
                "z_rapid_mmpm": self.z_rapid_mmpm,
            },
            "safe_positions": asdict(self.safe),
            "workholding": {
                "chuck_side": self.chuck_side.value,
                "chuck_diameter": self.chuck_diameter,
                "chuck_jaw_depth": self.chuck_jaw_depth,
                "bar_capacity": self.bar_capacity,
            },
            "coolant_available": self.coolant_available,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> "MachineConfig":
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))

        spindle = data.get("spindle", {})
        axes    = data.get("axes", {})
        safe    = data.get("safe_positions", {})
        wh      = data.get("workholding", {})

        return cls(
            name=data.get("name", "Lathe"),
            description=data.get("description", ""),
            max_spindle_rpm=spindle.get("max_rpm", 3000),
            min_spindle_rpm=spindle.get("min_rpm", 50),
            limits=AxisLimits(**axes.get("limits", {})),
            safe=SafePositions(**safe),
            x_rapid_mmpm=axes.get("x_rapid_mmpm", 0.0),
            z_rapid_mmpm=axes.get("z_rapid_mmpm", 0.0),
            chuck_side=ChuckSide(wh.get("chuck_side", "left")),
            chuck_diameter=wh.get("chuck_diameter", 200.0),
            chuck_jaw_depth=wh.get("chuck_jaw_depth", 40.0),
            bar_capacity=wh.get("bar_capacity", 52.0),
            coolant_available=data.get("coolant_available", True),
        )

    @classmethod
    def default(cls) -> "MachineConfig":
        """Return a MachineConfig with sensible defaults (no file required)."""
        return cls()
