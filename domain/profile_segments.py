"""
Geometric segment types for a 2D lathe profile (X-Z plane).

LineSegment  — straight move → G1
ArcSegment   — circular arc  → G2 / G3
Segment      — union type used throughout the CAM pipeline

All X coordinates are stored as *radius* (mm), not diameter.
Z coordinates are axial positions (0 at face, negative into part).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto


class ArcDirection(Enum):
    CW  = auto()   # G2 — clockwise in X-Z plane (convex external corner)
    CCW = auto()   # G3 — counter-clockwise (concave / fillet)


@dataclass(frozen=True)
class LineSegment:
    """Straight move from (x0, z0) to (x1, z1) — maps to G1."""
    x0: float   # radius
    z0: float
    x1: float   # radius
    z1: float

    @property
    def length(self) -> float:
        return math.hypot(self.x1 - self.x0, self.z1 - self.z0)

    def points(self, _resolution: int = 0) -> list[tuple[float, float]]:
        """Return the two endpoints as (x_radius, z) tuples."""
        return [(self.x0, self.z0), (self.x1, self.z1)]


@dataclass(frozen=True)
class ArcSegment:
    """
    Circular arc from (x0, z0) to (x1, z1) with centre at (cx, cz).
    Direction follows G2/G3 convention in the X-Z plane (G18).
    """
    x0: float       # radius
    z0: float
    x1: float       # radius
    z1: float
    cx: float       # arc centre, radius coordinate
    cz: float       # arc centre, Z coordinate
    radius: float
    direction: ArcDirection

    @property
    def angle_start(self) -> float:
        return math.atan2(self.z0 - self.cz, self.x0 - self.cx)

    @property
    def angle_end(self) -> float:
        return math.atan2(self.z1 - self.cz, self.x1 - self.cx)

    @property
    def sweep_angle(self) -> float:
        """Signed sweep in radians (positive = CCW)."""
        sweep = self.angle_end - self.angle_start
        if self.direction == ArcDirection.CCW and sweep < 0:
            sweep += 2 * math.pi
        elif self.direction == ArcDirection.CW and sweep > 0:
            sweep -= 2 * math.pi
        return sweep

    def points(self, resolution: int = 32) -> list[tuple[float, float]]:
        """
        Approximate the arc with *resolution* line segments.
        Used when exporting to a flat polygon for pyclipper.
        """
        sweep = self.sweep_angle
        pts: list[tuple[float, float]] = []
        for i in range(resolution + 1):
            a = self.angle_start + sweep * (i / resolution)
            pts.append((
                self.cx + self.radius * math.cos(a),
                self.cz + self.radius * math.sin(a),
            ))
        return pts


# Union type — used by LatheProfile, CAM engine, and G-code writer
Segment = LineSegment | ArcSegment
