"""cam/collision.py — trailing-angle clearance check for profile segments.

For a right-hand external tool: trailing_angle = 180 - approach_angle - insert_angle.
A narrowing profile steeper than the trailing angle will cause the rear of the
holder to dig into the workpiece (rear-collision / undercutting).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from domain.profile_segments import LineSegment

if TYPE_CHECKING:
    from domain.profile import LatheProfile
    from domain.tool import Tool


def check_trailing_clearance(profile: "LatheProfile", tool: "Tool | None") -> list[str]:
    """Return warning strings for segments that exceed the tool's trailing angle.

    An empty list means no issues detected.
    Each warning is a plain string (caller wraps it in a G-code comment).
    """
    if tool is None:
        return []
    trailing = 180.0 - tool.holder.approach_angle - tool.insert.cutting_angle
    if trailing <= 0:
        return []

    warnings: list[str] = []
    for seg in profile.segments():
        if not isinstance(seg, LineSegment):
            continue
        dx = seg.x1 - seg.x0   # radius change (+= widening)
        dz = seg.z1 - seg.z0   # axial change
        if abs(dz) < 1e-6 or dx >= 0:
            continue            # facing move or widening — safe
        slope = math.degrees(math.atan2(abs(dx), abs(dz)))
        if slope > trailing - 1.0:  # 1° safety buffer
            tag_str = f"op({seg.tag[0]},{seg.tag[1]})" if seg.tag else "?"
            warnings.append(
                f"COLLISION WARNING [{tag_str}]: slope {slope:.1f}° > "
                f"trailing {trailing:.1f}° "
                f"(approach={tool.holder.approach_angle:.0f}° "
                f"insert={tool.insert.cutting_angle:.0f}°)"
            )
    return warnings
