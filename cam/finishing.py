"""
CAM finishing pass generator.

Walks LatheProfile.to_gcode_segments() and emits G-code motion lines:
  LineSegment → G1 X{d} Z{z} F{feed}
  ArcSegment  → G2/G3 X{d} Z{z} I{i} K{k} F{feed}

Tool-radius compensation wrapping (optional):
  external  → G42 D{tool_id} ... G40
  internal  → G41 D{tool_id} ... G40

The caller (GCodeWriter) collects these lines and embeds them in the
full program; this module only concerns itself with the contour moves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.profile_segments import ArcDirection, ArcSegment, LineSegment, Segment

if TYPE_CHECKING:
    from domain.profile import LatheProfile


@dataclass
class FinishingLine:
    """One G-code motion line for the finishing contour."""
    text: str        # the complete G-code line (e.g. "G1 X25.400 Z-30.000 F120")
    is_rapid: bool = False


def _fmt(v: float) -> str:
    """Format a coordinate to 3 decimal places."""
    return f"{v:.3f}"


def _line_to_gcode(seg: LineSegment, feed: float) -> str:
    d  = seg.x1 * 2.0
    return f"G1 X{_fmt(d)} Z{_fmt(seg.z1)} F{feed:.0f}"


def _arc_to_gcode(seg: ArcSegment, feed: float) -> str:
    d  = seg.x1 * 2.0
    # IJK offsets from segment start to arc centre (incremental)
    i  = seg.cx - seg.x0
    k  = seg.cz - seg.z0
    g  = "G2" if seg.direction == ArcDirection.CW else "G3"
    return f"{g} X{_fmt(d)} Z{_fmt(seg.z1)} I{_fmt(i)} K{_fmt(k)} F{feed:.0f}"


# ---------------------------------------------------------------------------

class FinishingPass:
    """
    Generates finishing contour moves from a LatheProfile.

    Parameters
    ----------
    profile      : the finished part profile
    feed_rate    : cutting feed (mm/min)
    tool_id      : tool number for G41/G42 compensation (0 = no compensation)
    internal     : if True, use G41 instead of G42
    approach_z   : Z position for the approach rapid before the contour
    approach_r   : radius for the clearance rapid before the contour
    retract_r    : radius to retract to after the contour
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
    ) -> None:
        self._profile    = profile
        self._feed_rate  = feed_rate
        self._tool_id    = tool_id
        self._internal   = internal
        self._approach_z = approach_z
        # Default clearance: stock radius + 5 mm
        self._approach_r = approach_r if approach_r is not None else (
            profile.stock_d / 2.0 + 5.0
        )
        self._retract_r  = retract_r if retract_r is not None else self._approach_r

    # ------------------------------------------------------------------

    def generate(self) -> list[FinishingLine]:
        lines: list[FinishingLine] = []
        segments = self._profile.to_gcode_segments()

        if not segments:
            return lines

        # --- approach rapid -----------------------------------------------
        first_seg = segments[0]
        start_d   = first_seg.x0 * 2.0
        lines.append(FinishingLine(
            f"G0 X{_fmt(self._approach_r * 2.0)} Z{_fmt(self._approach_z)}",
            is_rapid=True,
        ))
        lines.append(FinishingLine(
            f"G0 X{_fmt(start_d)} Z{_fmt(self._approach_z)}",
            is_rapid=True,
        ))

        # --- tool-radius compensation on ------------------------------------
        if self._tool_id > 0:
            comp = "G41" if self._internal else "G42"
            lines.append(FinishingLine(f"{comp} D{self._tool_id}"))

        # --- contour moves --------------------------------------------------
        for seg in segments:
            if isinstance(seg, LineSegment):
                lines.append(FinishingLine(_line_to_gcode(seg, self._feed_rate)))
            elif isinstance(seg, ArcSegment):
                lines.append(FinishingLine(_arc_to_gcode(seg, self._feed_rate)))

        # --- tool-radius compensation off ----------------------------------
        if self._tool_id > 0:
            lines.append(FinishingLine("G40"))

        # --- retract rapid -------------------------------------------------
        lines.append(FinishingLine(
            f"G0 X{_fmt(self._retract_r * 2.0)}",
            is_rapid=True,
        ))

        return lines

    # ------------------------------------------------------------------
    # Convenience: return only the G-code strings (no metadata)
    # ------------------------------------------------------------------

    def lines(self) -> list[str]:
        return [fl.text for fl in self.generate()]
