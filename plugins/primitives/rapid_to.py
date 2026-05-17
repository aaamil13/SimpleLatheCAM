"""
Primitive: RapidTo — explicit rapid positioning move.

Category: Machine

This primitive does NOT add geometry to the LatheProfile.
It inserts a G00 positioning move into the G-code output stream — useful
for moving the tool to a safe position between operations, or for positioning
before an operation that does not start from the stock surface.

The GCodeWriter checks for RapidTo operations in the recipe and emits them
as G00 blocks rather than passing them to the CAM engine.

Validation checks the target coordinates against MachineConfig.limits if a
MachineConfig is available in the ProfileContext.  When no config is loaded
(simulation / development mode) the validation falls back to a wide safe range.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


# Fallback limits used when no MachineConfig is injected
_FALLBACK_X_MAX_RADIUS = 300.0
_FALLBACK_Z_MIN        = -1000.0
_FALLBACK_Z_MAX        = 100.0


class RapidToPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "rapid_to"

    @property
    def display_name(self) -> str:
        return "Бърз ход"

    @property
    def category(self) -> str:
        return "Machine"

    @property
    def tooltip(self) -> str:
        return (
            "Бърз позиционен ход (G00) до зададена позиция.\n"
            "Не добавя геометрия — само вмъква G00 в G-кода."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec(
                "x_diameter", "Диаметър X",
                "mm", default=100.0, min_val=0.0, max_val=600.0,
                tooltip="Целеви диаметър (0 = ос на въртене)",
            ),
            ParamSpec(
                "z_target", "Позиция Z",
                "mm", default=5.0, min_val=-1000.0, max_val=100.0,
                tooltip="Целева Z позиция (положителна = пред лицето на детайла)",
            ),
        ]

    # ------------------------------------------------------------------
    # Validation — checks against machine limits from context
    # ------------------------------------------------------------------

    def validate(
        self,
        params: dict[str, float],
        context: ProfileContext,
    ) -> str | None:
        error = super().validate(params, context)
        if error:
            return error

        x_radius = params["x_diameter"] / 2.0
        z        = params["z_target"]

        # Use machine limits stored on the context if available
        machine = getattr(context, "machine", None)
        if machine is not None:
            return machine.validate_position(x_radius, z)

        # Fallback range check
        if x_radius > _FALLBACK_X_MAX_RADIUS:
            return (
                f"X диаметър {params['x_diameter']:.1f} mm надвишава "
                f"максималния диаметър {_FALLBACK_X_MAX_RADIUS * 2:.0f} mm."
            )
        if not (_FALLBACK_Z_MIN <= z <= _FALLBACK_Z_MAX):
            return (
                f"Z {z:.1f} mm е извън допустимия обхват "
                f"[{_FALLBACK_Z_MIN}, {_FALLBACK_Z_MAX}]."
            )
        return None

    # ------------------------------------------------------------------
    # Build — intentionally a no-op for profile geometry
    # ------------------------------------------------------------------

    def build(self, profile: "LatheProfile", params: dict[str, float]) -> None:
        """
        RapidTo does not modify the profile.

        The GCodeWriter detects RapidTo operations by name and emits G00
        instead of calling the CAM engine.  The profile cursor is NOT
        updated here — the rapid move is a pure machine motion.
        """

    # ------------------------------------------------------------------
    # Icon — arrow symbol indicating a fast move
    # ------------------------------------------------------------------

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        """
        Draws a diagonal arrow suggesting a fast positioning move.
        """
        painter.save()

        m  = 6
        x0 = rect.left()   + m
        y0 = rect.top()    + m
        w  = rect.width()  - 2 * m
        h  = rect.height() - 2 * m
        mid_y = rect.center().y()

        pen = QPen(QColor("#EF5350"), 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Arrow shaft: bottom-left → top-right
        x1, y1 = x0,         mid_y + h // 3
        x2, y2 = x0 + w,     mid_y - h // 3

        painter.drawLine(x1, y1, x2, y2)

        # Arrowhead
        arrow_size = max(5, w // 5)
        angle = math.atan2(y1 - y2, x2 - x1)  # shaft direction
        left_angle  = angle + math.radians(150)
        right_angle = angle - math.radians(150)
        ax1 = int(x2 + arrow_size * math.cos(left_angle))
        ay1 = int(y2 - arrow_size * math.sin(left_angle))
        ax2 = int(x2 + arrow_size * math.cos(right_angle))
        ay2 = int(y2 - arrow_size * math.sin(right_angle))
        painter.drawLine(x2, y2, ax1, ay1)
        painter.drawLine(x2, y2, ax2, ay2)

        # Speed dashes (suggesting rapid motion)
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#EF9A9A"))
        pen.setWidth(1)
        painter.setPen(pen)
        for offset in (-4, 4):
            painter.drawLine(x1, y1 + offset, x2, y2 + offset)

        painter.restore()
