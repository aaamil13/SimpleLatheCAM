"""
Primitive: Chamfer (45° or custom angle bevel)

Inserts a chamfer at the current cursor position.  The chamfer connects
the current diameter to a new (smaller) diameter using a straight line
at the specified angle.

For a 45° chamfer of size S:
  - axial run   = S
  - radial drop = S  (i.e. diameter decreases by 2*S)

For a custom angle A (measured from the Z axis):
  - axial run   = S
  - radial drop = 2 * S * tan(A)   (diameter decreases by this amount)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class ChamferPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "chamfer"

    @property
    def display_name(self) -> str:
        return "Фаска"

    @property
    def category(self) -> str:
        return "Turning"

    @property
    def tooltip(self) -> str:
        return (
            "Фаска (скосяване) — задайте размер по оста Z и ъгъл. "
            "45° е стандартна фаска."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec(
                "size", "Размер (аксиален)",
                "mm", default=2.0, min_val=0.01, max_val=100.0,
                tooltip="Дължина на фаската по оста Z",
            ),
            ParamSpec(
                "angle", "Ъгъл",
                "deg", default=45.0, min_val=1.0, max_val=89.0,
                tooltip="Ъгъл на фаската спрямо оста Z. 45° = стандартна фаска.",
            ),
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        params: dict[str, float],
        context: ProfileContext,
    ) -> str | None:
        error = super().validate(params, context)
        if error:
            return error

        size  = params["size"]
        angle = params["angle"]
        radial_drop = 2.0 * size * math.tan(math.radians(angle))

        if radial_drop >= context.cursor_x:
            return (
                f"Фаската ще намали диаметъра с {radial_drop:.2f} mm, "
                f"но текущият диаметър е само {context.cursor_x:.2f} mm."
            )

        remaining_z = abs(context.cursor_z) + size
        if remaining_z > context.stock_l:
            return (
                f"Фаската надвишава дължината на заготовката "
                f"({context.stock_l} mm)."
            )
        return None

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def build(self, profile: "LatheProfile", params: dict[str, float]) -> None:
        size  = params["size"]
        angle = params["angle"]
        radial_drop = 2.0 * size * math.tan(math.radians(angle))
        new_d = profile.cursor_x - radial_drop
        profile.add_taper(d_end=new_d, length=size)

    # ------------------------------------------------------------------
    # Icon  (static symbolic sketch)
    # ------------------------------------------------------------------

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        """
        Draws a recognisable chamfer symbol:

            ────────┐
                     \
                      └────
        """
        painter.save()

        m   = 6
        x0  = rect.left()  + m
        y0  = rect.top()   + m
        w   = rect.width()  - 2 * m
        h   = rect.height() - 2 * m
        mid = rect.center().y()
        step = h // 3

        pen = QPen(QColor("#FFB74D"), 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        half_w = w // 2

        # Left cylinder (upper wall)
        painter.drawLine(x0, mid - step, x0 + half_w, mid - step)
        # Left cylinder (lower wall)
        painter.drawLine(x0, mid + step, x0 + half_w, mid + step)
        # Left cap
        painter.drawLine(x0, mid - step, x0, mid + step)

        # Chamfer lines (diagonal from upper to lower step)
        painter.drawLine(x0 + half_w, mid - step, x0 + w, mid)
        painter.drawLine(x0 + half_w, mid + step, x0 + w, mid)

        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
