"""
CAM roughing pass generator for external and internal turning.

Strategy
--------
1. Build a closed stock polygon (rectangle: r=0..stock_r, z=0..−stock_l).
2. Build the part profile polygon from LatheProfile.to_polygon().
3. Offset the part polygon outward by the tool nose radius (finishing allowance).
4. Subtract the offset part from the stock polygon using pyclipper to get the
   material-to-remove region.
5. Slice the removal region with horizontal (constant-X / constant-radius) lines
   spaced *step_down* apart.
6. Each slice → one RoughingPass (rapid to start, feed across, retract).

pyclipper uses integer coordinates — all floats are scaled by SCALE.

Exports
-------
  RoughingPass  — one radial depth-of-cut pass
  ExternalRougher — produces passes for external (OD) turning
  InternalRougher — produces passes for internal (ID) / boring
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

try:
    import pyclipper as _pc
    _HAVE_PYCLIPPER = True
except ImportError:
    _pc = None  # type: ignore[assignment]
    _HAVE_PYCLIPPER = False

if TYPE_CHECKING:
    from domain.profile import LatheProfile
    from domain.tool import Tool

# pyclipper integer scale factor (0.001 mm resolution)
_SCALE = 1_000


def _to_int(pts: list[tuple[float, float]]) -> list[tuple[int, int]]:
    return [(round(x * _SCALE), round(z * _SCALE)) for x, z in pts]


def _to_float(pts) -> list[tuple[float, float]]:
    return [(x / _SCALE, z / _SCALE) for x, z in pts]


# ---------------------------------------------------------------------------

@dataclass
class RoughingPass:
    """One constant-radius turning pass."""
    radius: float                   # depth at which this pass runs (mm, radius)
    moves: list[tuple[float, float]]  # ordered (radius, z) feed moves
    feed_rate: float                # mm/min


# ---------------------------------------------------------------------------

def _stock_polygon(stock_r: float, stock_l: float) -> list[tuple[float, float]]:
    """Closed rectangle representing full stock cross-section (radius coords)."""
    return [
        (0.0,     0.0),
        (stock_r, 0.0),
        (stock_r, -stock_l),
        (0.0,     -stock_l),
    ]


def _close_profile_polygon(
    profile_pts: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """
    Close the open profile path into a filled polygon suitable for pyclipper.

    The profile path is the machined outer surface (open, left to right in R-Z).
    Close it through the centreline:
      last point → (0, last_z) → (0, 0) → first point  (pyclipper closes implicitly)
    """
    if not profile_pts:
        return []
    closed = list(profile_pts)
    last_r, last_z = profile_pts[-1]
    first_z = profile_pts[0][1]
    # Plunge to centreline at end Z
    if abs(last_r) > 1e-6:
        closed.append((0.0, last_z))
    # Return along centreline to Z=0 (face datum)
    if abs(last_z) > 1e-6:
        closed.append((0.0, first_z))
    return closed


def _offset_polygon(
    pts: list[tuple[float, float]],
    delta: float,
    join_type=None,
) -> list[tuple[float, float]]:
    """Outward pyclipper offset of a closed polygon by *delta* mm."""
    if not _HAVE_PYCLIPPER or _pc is None:
        return pts
    if join_type is None:
        join_type = _pc.JT_ROUND  # type: ignore[attr-defined]
    pco = _pc.PyclipperOffset()   # type: ignore[attr-defined]
    pco.AddPath(_to_int(pts), join_type, _pc.ET_CLOSEDPOLYGON)  # type: ignore[attr-defined]
    results = pco.Execute(round(delta * _SCALE))
    if not results:
        return pts
    return _to_float(results[0])


def _clip_difference(
    subject: list[tuple[float, float]],
    clip: list[tuple[float, float]],
) -> list[list[tuple[float, float]]]:
    """subject − clip using pyclipper DIFFERENCE."""
    if not _HAVE_PYCLIPPER or _pc is None:
        return [subject]
    pc = _pc.Pyclipper()                                          # type: ignore[attr-defined]
    pc.AddPath(_to_int(subject), _pc.PT_SUBJECT, True)            # type: ignore[attr-defined]
    pc.AddPath(_to_int(clip),    _pc.PT_CLIP,    True)            # type: ignore[attr-defined]
    results = pc.Execute(
        _pc.CT_DIFFERENCE,   # type: ignore[attr-defined]
        _pc.PFT_NONZERO,     # type: ignore[attr-defined]
        _pc.PFT_NONZERO,     # type: ignore[attr-defined]
    )
    return [_to_float(r) for r in results]


def _z_range_of(polygons: list[list[tuple[float, float]]]) -> tuple[float, float]:
    all_z = [z for poly in polygons for _, z in poly]
    return min(all_z), max(all_z)


def _r_range_of(polygons: list[list[tuple[float, float]]]) -> tuple[float, float]:
    all_r = [r for poly in polygons for r, _ in poly]
    return min(all_r), max(all_r)


def _horizontal_slice(
    polygons: list[list[tuple[float, float]]],
    r_level: float,
    z_min: float,
    z_max: float,
) -> list[tuple[float, float]] | None:
    """
    Find the Z extents where the removal region exists at radius *r_level*.
    Returns a list of (z_start, z_end) segments or None if nothing to cut.
    """
    segments: list[tuple[float, float]] = []
    for poly in polygons:
        n = len(poly)
        crossings: list[float] = []
        for i in range(n):
            r0, z0 = poly[i]
            r1, z1 = poly[(i + 1) % n]
            if (r0 <= r_level < r1) or (r1 <= r_level < r0):
                t = (r_level - r0) / (r1 - r0)
                crossings.append(z0 + t * (z1 - z0))
        crossings.sort()
        for j in range(0, len(crossings) - 1, 2):
            segments.append((crossings[j], crossings[j + 1]))
    return segments if segments else None


# ---------------------------------------------------------------------------

class ExternalRougher:
    """
    Generates OD roughing passes for a turned part.

    Parameters
    ----------
    profile       : finished LatheProfile
    stock_r       : original stock radius (mm)
    stock_l       : original stock length (mm)
    step_down     : radial depth per pass (mm)
    feed_rate     : cutting feed rate (mm/min)
    finish_allowance : radial stock left for finishing pass (mm)
    nose_radius   : tool nose radius used for offset (mm)
    """

    def __init__(
        self,
        profile: "LatheProfile",
        stock_r: float,
        stock_l: float,
        step_down: float = 1.0,
        feed_rate: float = 150.0,
        finish_allowance: float = 0.3,
        nose_radius: float = 0.4,
    ) -> None:
        self._profile      = profile
        self._stock_r      = stock_r
        self._stock_l      = stock_l
        self._step_down    = max(step_down, 0.05)
        self._feed_rate    = feed_rate
        self._allowance    = finish_allowance
        self._nose_radius  = nose_radius

    def generate(self) -> list[RoughingPass]:
        part_pts   = _close_profile_polygon(self._profile.to_polygon())
        offset_amt = self._allowance + self._nose_radius
        offset_pts = _offset_polygon(part_pts, offset_amt) if offset_amt > 0 else part_pts

        stock_pts  = _stock_polygon(self._stock_r, self._stock_l)
        removal    = _clip_difference(stock_pts, offset_pts)

        if not removal:
            return []

        r_min, r_max = _r_range_of(removal)
        z_min, z_max = _z_range_of(removal)

        passes: list[RoughingPass] = []
        # Start from stock surface, step inward
        r = self._stock_r - self._step_down
        while r >= r_min - 1e-6:
            segs = _horizontal_slice(removal, r, z_min, z_max)
            if segs:
                for z_start, z_end in segs:
                    # Sort so we cut from positive Z toward negative Z
                    z_a = max(z_start, z_end)
                    z_b = min(z_start, z_end)
                    passes.append(RoughingPass(
                        radius=r,
                        moves=[(r, z_a), (r, z_b)],
                        feed_rate=self._feed_rate,
                    ))
            r -= self._step_down
            if r < r_min - self._step_down:
                break

        return passes

# ---------------------------------------------------------------------------

class InternalRougher:
    """
    Generates ID / boring roughing passes.

    The stock is assumed to be solid (or have a pre-drilled bore_r).
    Passes step *outward* from the bore toward the finished profile.
    """

    def __init__(
        self,
        profile: "LatheProfile",
        bore_r: float,
        stock_l: float,
        step_down: float = 0.5,
        feed_rate: float = 80.0,
        finish_allowance: float = 0.2,
        nose_radius: float = 0.4,
    ) -> None:
        self._profile     = profile
        self._bore_r      = bore_r
        self._stock_l     = stock_l
        self._step_down   = max(step_down, 0.05)
        self._feed_rate   = feed_rate
        self._allowance   = finish_allowance
        self._nose_radius = nose_radius

    def generate(self) -> list[RoughingPass]:
        part_pts   = _close_profile_polygon(self._profile.to_polygon())
        # Inward offset — leave finishing allowance on the bore wall
        offset_amt = -(self._allowance + self._nose_radius)
        offset_pts = _offset_polygon(part_pts, offset_amt) if offset_amt < 0 else part_pts

        # "Stock" for boring = the finished bore region (offset_pts minus bore)
        bore_pts  = _stock_polygon(self._bore_r, self._stock_l)
        removal   = _clip_difference(offset_pts, bore_pts)

        if not removal:
            return []

        r_min, r_max = _r_range_of(removal)
        z_min, z_max = _z_range_of(removal)

        passes: list[RoughingPass] = []
        r = self._bore_r + self._step_down
        while r <= r_max + 1e-6:
            segs = _horizontal_slice(removal, r, z_min, z_max)
            if segs:
                for z_start, z_end in segs:
                    z_a = max(z_start, z_end)
                    z_b = min(z_start, z_end)
                    passes.append(RoughingPass(
                        radius=r,
                        moves=[(r, z_a), (r, z_b)],
                        feed_rate=self._feed_rate,
                    ))
            r += self._step_down

        return passes
