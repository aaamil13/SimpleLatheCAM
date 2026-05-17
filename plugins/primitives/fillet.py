"""
Primitive: Fillet — tangent arc at the current corner.

Inserts a radius blend between the previous segment and the next one.
Convex (default): outward relief on an external shoulder — G2.
Concave:          undercut / internal fillet — G3.

The previous LineSegment is automatically trimmed by the setback distance
(equal to the fillet radius for a 90° corner).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class FilletPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "fillet"

    @property
    def display_name(self) -> str:
        return "Радиус"

    @property
    def category(self) -> str:
        return "Turning"

    @property
    def min_segments(self) -> int:
        return 1   # needs a previous segment to trim and arc from

    @property
    def tooltip(self) -> str:
        return (
            "Радиусно скосяване на ъгъл.\n"
            "Изпъкнал (по подразбиране): облекчение на рамо (G2).\n"
            "Вдлъбнат: подрязване (G3)."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("radius",  "Радиус",    "mm",
                      default=2.0, min_val=0.1, max_val=50.0),
            ParamSpec("concave", "Вдлъбнат",  "",
                      default=0.0, min_val=0.0, max_val=1.0,
                      tooltip="0 = изпъкнал (G2), 1 = вдлъбнат (G3)"),
        ]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        if context.segment_count == 0:
            return "Радиусът изисква поне един предходен сегмент."
        r = params["radius"]
        # Rough check: fillet must not exceed half the current diameter
        if r * 2 > context.cursor_x:
            return (
                f"Радиус {r} mm е прекалено голям за текущия "
                f"диаметър {context.cursor_x:.1f} mm."
            )
        return None

    def build(self, profile: "LatheProfile", params: dict) -> None:
        profile.add_fillet(
            radius=params["radius"],
            concave=bool(round(params["concave"])),
        )

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        m   = 6
        x0  = rect.left() + m
        w   = rect.width() - 2 * m
        h   = rect.height() - 2 * m
        mid = rect.center().y()
        step = h // 3

        pen = QPen(QColor("#CE93D8"), 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        half_w = w // 2
        # Left cylinder top / bottom walls
        painter.drawLine(x0, mid - step, x0 + half_w, mid - step)
        painter.drawLine(x0, mid + step, x0 + half_w, mid + step)
        painter.drawLine(x0, mid - step, x0, mid + step)

        # Right smaller cylinder
        painter.drawLine(x0 + half_w + step // 2, mid - step // 2, x0 + w, mid - step // 2)
        painter.drawLine(x0 + half_w + step // 2, mid + step // 2, x0 + w, mid + step // 2)

        # Arc connecting the two (convex fillet)
        from PySide6.QtCore import QRect as QR
        arc_rect = QR(
            x0 + half_w - step // 2,
            mid - step,
            step,
            step,
        )
        painter.drawArc(arc_rect, 0 * 16, 90 * 16)

        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
