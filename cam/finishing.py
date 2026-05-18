"""
CAM finishing pass generator.

Walks the tool-centre-point path (offset from LatheProfile by nose_radius via
cam.profile_offset) and emits G1 linear feed moves.  Arc segments from the
profile are linearised to the same arc_resolution used in to_polygon().

G41/G42 controller compensation is NOT used — the offset is computed
explicitly so the output works on any controller.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cam.profile_offset import offset_profile_polygon

if TYPE_CHECKING:
    from domain.profile import LatheProfile


@dataclass
class FinishingLine:
    """One G-code motion line for the finishing contour."""
    text: str
    is_rapid: bool = False


def _fmt(v: float) -> str:
    return f"{v:.3f}"


# ---------------------------------------------------------------------------

class FinishingPass:
    """
    Generates finishing contour moves from a LatheProfile.

    Parameters
    ----------
    profile       : the finished part profile
    feed_rate     : cutting feed (mm/min)
    tool_id       : kept for API compatibility (no longer used for G41/G42)
    internal      : boring pass — offset inward
    approach_z    : Z clearance above part start for the approach rapid
    approach_r    : clearance radius before contour (rapid)
    retract_r     : radius to retract to after contour
    nose_radius   : tool nose radius for TCP offset (mm); 0 = no offset
    arc_resolution: points per arc when linearising profile arcs
    """

    def __init__(
        self,
        profile: "LatheProfile",
        feed_rate: float = 120.0,
        tool_id: int = 0,
        internal: bool = False,
        approach_z: float = 2.0,
        approach_r: float | None = None,
        retract_r: float | None = None,
        nose_radius: float = 0.0,
        arc_resolution: int = 32,
    ) -> None:
        self._profile        = profile
        self._feed_rate      = feed_rate
        self._internal       = internal
        self._approach_z     = approach_z
        self._nose_radius    = nose_radius
        self._arc_resolution = arc_resolution
        fallback_r = profile.stock_d / 2.0 + 5.0
        self._approach_r = approach_r if approach_r is not None else fallback_r
        self._retract_r  = retract_r  if retract_r  is not None else self._approach_r

    # ------------------------------------------------------------------

    def generate(self) -> list[FinishingLine]:
        pts = offset_profile_polygon(
            self._profile,
            self._nose_radius,
            self._internal,
        )
        if not pts:
            return []

        lines: list[FinishingLine] = []

        # approach rapids
        start_d = pts[0][0] * 2.0
        lines.append(FinishingLine(
            f"G0 X{_fmt(self._approach_r * 2.0)} Z{_fmt(self._approach_z)}",
            is_rapid=True,
        ))
        lines.append(FinishingLine(
            f"G0 X{_fmt(start_d)} Z{_fmt(self._approach_z)}",
            is_rapid=True,
        ))

        # plunge to first Z
        first_z = pts[0][1]
        lines.append(FinishingLine(
            f"G1 X{_fmt(start_d)} Z{_fmt(first_z)} F{self._feed_rate:.0f}"
        ))

        # contour feed moves
        for r, z in pts[1:]:
            lines.append(FinishingLine(
                f"G1 X{_fmt(r * 2.0)} Z{_fmt(z)} F{self._feed_rate:.0f}"
            ))

        # retract
        lines.append(FinishingLine(
            f"G0 X{_fmt(self._retract_r * 2.0)}",
            is_rapid=True,
        ))

        return lines

    def lines(self) -> list[str]:
        return [fl.text for fl in self.generate()]
