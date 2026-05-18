"""
LatheProfile — ordered 2D contour of a turned part in the X-Z plane.

Coordinate convention
---------------------
  cursor_x  — current *diameter* (mm).  Radius is used internally.
  cursor_z  — axial position (0 = face datum, negative = into part).

All public add_* methods accept diameter (D) values, not radius.
Segments are stored as radius for geometry calculations.

Exports
-------
  to_polygon(arc_resolution)  — flat (x_radius, z) list for pyclipper
  to_gcode_segments()         — typed Segment list for the G-code writer
"""

from __future__ import annotations

import math
from typing import Iterator

from domain.primitive_base import ProfileContext
from domain.profile_segments import ArcDirection, ArcSegment, LineSegment, Segment


class LatheProfile:

    def __init__(self, stock_d: float, stock_l: float) -> None:
        if stock_d <= 0:
            raise ValueError(f"stock_d must be positive, got {stock_d}")
        if stock_l <= 0:
            raise ValueError(f"stock_l must be positive, got {stock_l}")

        self.stock_d = stock_d
        self.stock_l = stock_l
        self._segments: list[Segment] = []
        self._cursor_r: float = stock_d / 2.0   # internal: radius
        self._cursor_z: float = 0.0
        self.active_tag: tuple[int, int] | None = None  # set by EditorModel._rebuild

    # ------------------------------------------------------------------
    # Cursor (diameter-facing public API)
    # ------------------------------------------------------------------

    @property
    def cursor_x(self) -> float:
        """Current diameter (mm)."""
        return self._cursor_r * 2.0

    @cursor_x.setter
    def cursor_x(self, diameter: float) -> None:
        self._cursor_r = diameter / 2.0

    @property
    def cursor_r(self) -> float:
        """Current radius (mm)."""
        return self._cursor_r

    @property
    def cursor_z(self) -> float:
        return self._cursor_z

    @property
    def segment_count(self) -> int:
        return len(self._segments)

    def context(self) -> ProfileContext:
        """Snapshot passed to plug-in validate / build."""
        return ProfileContext(
            cursor_x=self.cursor_x,
            cursor_z=self._cursor_z,
            stock_d=self.stock_d,
            stock_l=self.stock_l,
            segment_count=len(self._segments),
        )

    # ------------------------------------------------------------------
    # Primitive builders
    # ------------------------------------------------------------------

    def add_cylinder(self, d: float, length: float) -> None:
        """Straight step at diameter *d* for axial *length*.
        A radial face move is inserted automatically when *d* differs
        from the current diameter."""
        r  = d / 2.0
        z0 = self._cursor_z
        z1 = z0 - length
        if not math.isclose(r, self._cursor_r, abs_tol=1e-6):
            self._segments.append(LineSegment(self._cursor_r, z0, r, z0, tag=self.active_tag))
            self._cursor_r = r
        self._segments.append(LineSegment(r, z0, r, z1, tag=self.active_tag))
        self._cursor_z = z1

    def add_taper(self, d_end: float, length: float) -> None:
        """Straight taper from the current diameter to *d_end* over *length*."""
        r_end = d_end / 2.0
        z0    = self._cursor_z
        z1    = z0 - length
        self._segments.append(LineSegment(self._cursor_r, z0, r_end, z1, tag=self.active_tag))
        self._cursor_r = r_end
        self._cursor_z = z1

    def add_fillet(self, radius: float, concave: bool = False) -> None:
        """Insert a tangent arc at the current corner.

        *concave=False*: convex shoulder fillet (G2, outward relief).
        *concave=True*:  concave undercut fillet (G3).

        Raises ValueError when the radius exceeds the previous segment length.
        """
        if not self._segments:
            raise ValueError("Cannot add fillet: no previous segment exists.")
        prev = self._segments[-1]
        if not isinstance(prev, LineSegment):
            raise ValueError("Cannot add fillet after an arc segment.")

        dx, dz   = prev.x1 - prev.x0, prev.z1 - prev.z0
        seg_len  = math.hypot(dx, dz)
        if seg_len < 1e-9:
            raise ValueError("Previous segment has zero length.")
        tx, tz   = dx / seg_len, dz / seg_len

        if concave:
            nx, nz    = tz, -tx
            direction = ArcDirection.CCW
        else:
            nx, nz    = -tz, tx
            direction = ArcDirection.CW

        if seg_len < radius + 1e-6:
            raise ValueError(
                f"Fillet radius {radius} mm is too large for the previous "
                f"segment (length {seg_len:.3f} mm)."
            )

        cx = prev.x1 + nx * radius
        cz = prev.z1 + nz * radius
        x_start = prev.x1 - tx * radius
        z_start = prev.z1 - tz * radius
        x_end   = cx + radius * (-nx)
        z_end   = cz + radius * (-nz)

        # Trim previous segment, preserving its operation tag
        self._segments[-1] = LineSegment(prev.x0, prev.z0, x_start, z_start, tag=prev.tag)
        self._segments.append(ArcSegment(
            x0=x_start, z0=z_start,
            x1=x_end,   z1=z_end,
            cx=cx, cz=cz,
            radius=radius,
            direction=direction,
            tag=self.active_tag,
        ))
        self._cursor_r = x_end
        self._cursor_z = z_end

    def add_line_to(self, d: float, z: float) -> None:
        """Absolute line move to diameter *d* at axial position *z*."""
        r = d / 2.0
        self._segments.append(LineSegment(self._cursor_r, self._cursor_z, r, z, tag=self.active_tag))
        self._cursor_r = r
        self._cursor_z = z

    def add_face(self, depth: float = 0.0) -> None:
        """Radial sweep from current diameter to axis (D=0).
        Advances Z by *depth* if given."""
        z0 = self._cursor_z
        z1 = z0 - depth if depth > 0 else z0
        self._segments.append(LineSegment(self._cursor_r, z0, 0.0, z0, tag=self.active_tag))
        if not math.isclose(z0, z1, abs_tol=1e-6):
            self._segments.append(LineSegment(0.0, z0, 0.0, z1, tag=self.active_tag))
        self._cursor_r = 0.0
        self._cursor_z = z1

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_polygon(self, arc_resolution: int = 32) -> list[tuple[float, float]]:
        """Flat (x_radius, z) point list for pyclipper. Deduplicates joins."""
        pts: list[tuple[float, float]] = []
        for seg in self._segments:
            new_pts = seg.points(arc_resolution)
            if pts and pts[-1] == new_pts[0]:
                new_pts = new_pts[1:]
            pts.extend(new_pts)
        return pts

    def to_gcode_segments(self) -> list[Segment]:
        """Copy of the segment list for the G-code writer."""
        return list(self._segments)

    def segments(self) -> Iterator[Segment]:
        yield from self._segments

    def bounding_box(self) -> tuple[float, float, float, float]:
        """(min_r, max_r, min_z, max_z) over all segment endpoints."""
        pts = self.to_polygon(arc_resolution=0)
        xs = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        return min(xs), max(xs), min(zs), max(zs)

    def __repr__(self) -> str:
        return (
            f"LatheProfile(stock_d={self.stock_d}, stock_l={self.stock_l}, "
            f"segments={len(self._segments)}, "
            f"cursor=({self.cursor_x:.2f}D, {self._cursor_z:.2f}Z))"
        )
