"""
Primitive: Cylinder (straight turning step)

Adds a cylindrical section at diameter D for length L along Z.
This is the most common primitive — used for every straight shaft step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class CylinderPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "cylinder"

    @property
    def display_name(self) -> str:
        return "Цилиндър"

    @property
    def category(self) -> str:
        return "Turning"

    @property
    def tooltip(self) -> str:
        return "Прав цилиндричен стъпал — задайте диаметър и дължина."

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("D", "Диаметър", "mm", default=30.0, min_val=0.1, max_val=1000.0,
                      tooltip="Диаметърът на цилиндъра"),
            ParamSpec("L", "Дължина",  "mm", default=20.0, min_val=0.1, max_val=2000.0,
                      tooltip="Дължина по оста Z"),
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

        d = params["D"]
        if d > context.stock_d:
            return (
                f"Диаметър {d} mm надвишава диаметъра на заготовката "
                f"({context.stock_d} mm)."
            )
        remaining_z = abs(context.cursor_z) + params["L"]
        if remaining_z > context.stock_l:
            return (
                f"Общата дължина {remaining_z:.2f} mm надвишава дължината на "
                f"заготовката ({context.stock_l} mm)."
            )
        return None

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def build(self, profile: "LatheProfile", params: dict[str, float]) -> None:
        profile.add_cylinder(d=params["D"], length=params["L"])

    # ------------------------------------------------------------------
    # Icon  (static symbolic sketch — no params)
    # ------------------------------------------------------------------

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        """
        Draws a simple rectangular cross-section symbol representing a
        turned cylinder step:

            ┌────────────┐
            │            │   ← top wall (constant diameter)
            └────────────┘
        """
        painter.save()

        m = 6   # margin
        x0 = rect.left() + m
        y0 = rect.top() + m
        w  = rect.width()  - 2 * m
        h  = rect.height() - 2 * m
        mid_y = rect.center().y()
        step_h = h // 3

        pen = QPen(QColor("#4FC3F7"), 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Top wall
        painter.drawLine(x0, mid_y - step_h, x0 + w, mid_y - step_h)
        # Bottom wall
        painter.drawLine(x0, mid_y + step_h, x0 + w, mid_y + step_h)
        # Left cap
        painter.drawLine(x0, mid_y - step_h, x0, mid_y + step_h)
        # Right cap (open — continues to next segment)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(x0 + w, mid_y - step_h, x0 + w, mid_y + step_h)
        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        painter.setPen(pen)
        painter.drawLine(x0, mid_y, x0 + w, mid_y)

        painter.restore()
