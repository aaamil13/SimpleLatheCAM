"""
Primitive: Groove — rectangular groove (external or internal).

A groove is cut at axial position Z_center with a blade of width W.
The blade plunges radially to depth D_groove from the current surface.

External groove: cuts inward (reduces diameter).
Internal groove:  cuts outward (enlarges bore diameter at that position).

The profile records the groove as three segments:
  entry wall (radial) → groove floor (axial, width W) → exit wall (radial)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class GroovePrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "groove"

    @property
    def display_name(self) -> str:
        return "Жлеб"

    @property
    def category(self) -> str:
        return "Turning"

    @property
    def tooltip(self) -> str:
        return "Правоъгълен жлеб — зададете ширина, дълбочина и позиция."

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("width",   "Ширина",    "mm",
                      default=3.0, min_val=0.5, max_val=50.0,
                      tooltip="Ширина на жлеба (равна на ширината на ножа)"),
            ParamSpec("depth",   "Дълбочина", "mm",
                      default=3.0, min_val=0.1, max_val=100.0,
                      tooltip="Радиална дълбочина на жлеба"),
            ParamSpec("z_offset", "Z отместване", "mm",
                      default=0.0, min_val=-500.0, max_val=0.0,
                      tooltip="Аксиална позиция спрямо текущия курсор (0 = тук)"),
        ]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        depth = params["depth"]
        if depth * 2 >= context.cursor_x:
            return (
                f"Дълбочина {depth} mm ще надхвърли центъра при "
                f"текущ диаметър {context.cursor_x:.1f} mm."
            )
        z_abs = context.cursor_z + params["z_offset"]
        if z_abs < -context.stock_l:
            return "Позицията на жлеба е извън дължината на заготовката."
        return None

    def build(self, profile: "LatheProfile", params: dict) -> None:
        width   = params["width"]
        depth   = params["depth"]
        z_start = profile.cursor_z + params["z_offset"]
        z_end   = z_start - width

        surface_r = profile._cursor_r
        floor_r   = surface_r - depth

        # Move to groove start (radial plunge)
        profile.add_line_to(d=floor_r * 2, z=z_start)
        # Groove floor
        profile.add_line_to(d=floor_r * 2, z=z_end)
        # Exit wall (radial return)
        profile.add_line_to(d=surface_r * 2, z=z_end)

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        m   = 6
        x0  = rect.left() + m
        w   = rect.width() - 2 * m
        mid = rect.center().y()
        step = (rect.height() - 2 * m) // 3

        pen = QPen(QColor("#FFD54F"), 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        gx  = x0 + w // 2 - w // 8   # groove left edge
        gx2 = x0 + w // 2 + w // 8   # groove right edge
        gd  = step                     # groove depth in pixels

        # Outer surface (left of groove)
        painter.drawLine(x0, mid - step, gx, mid - step)
        painter.drawLine(x0, mid + step, gx, mid + step)
        # Groove walls and floor
        painter.drawLine(gx,  mid - step, gx,  mid - step + gd)
        painter.drawLine(gx,  mid - step + gd, gx2, mid - step + gd)
        painter.drawLine(gx2, mid - step, gx2, mid - step + gd)
        # Mirror bottom
        painter.drawLine(gx,  mid + step, gx,  mid + step - gd)
        painter.drawLine(gx,  mid + step - gd, gx2, mid + step - gd)
        painter.drawLine(gx2, mid + step, gx2, mid + step - gd)
        # Outer surface (right of groove)
        painter.drawLine(gx2, mid - step, x0 + w, mid - step)
        painter.drawLine(gx2, mid + step, x0 + w, mid + step)

        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
