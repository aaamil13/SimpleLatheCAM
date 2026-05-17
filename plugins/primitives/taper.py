"""
Primitive: Taper — conical step (D_start → D_end over length L).

The taper starts at the current cursor diameter and ends at D_end.
Positive taper: D_end < current diameter (narrowing toward chuck).
Negative taper: D_end > current diameter (widening — e.g. back taper).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class TaperPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "taper"

    @property
    def display_name(self) -> str:
        return "Конус"

    @property
    def category(self) -> str:
        return "External"

    @property
    def tooltip(self) -> str:
        return "Конусен стъпал — от текущия диаметър до D_end по дължина L."

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("d_end",  "Краен диаметър", "mm",
                      default=20.0, min_val=0.0, max_val=1000.0,
                      tooltip="Диаметър в края на конуса"),
            ParamSpec("length", "Дължина",        "mm",
                      default=20.0, min_val=0.1, max_val=2000.0),
        ]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        if params["d_end"] > context.stock_d:
            return (
                f"Краен диаметър {params['d_end']} mm надвишава "
                f"диаметъра на заготовката ({context.stock_d} mm)."
            )
        used_z = abs(context.cursor_z) + params["length"]
        if used_z > context.stock_l:
            return (
                f"Общата дължина {used_z:.2f} mm надвишава "
                f"дължината на заготовката ({context.stock_l} mm)."
            )
        return None

    def build(self, profile: "LatheProfile", params: dict) -> None:
        profile.add_taper(d_end=params["d_end"], length=params["length"])

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        m   = 6
        x0  = rect.left() + m
        w   = rect.width() - 2 * m
        mid = rect.center().y()
        step = (rect.height() - 2 * m) // 3

        pen = QPen(QColor("#81C784"), 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Top taper line: wide left → narrow right
        painter.drawLine(x0, mid - step, x0 + w, mid - step // 2)
        # Bottom mirror
        painter.drawLine(x0, mid + step, x0 + w, mid + step // 2)
        # Left cap (full diameter)
        painter.drawLine(x0, mid - step, x0, mid + step)
        # Right cap (smaller diameter, dashed)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(x0 + w, mid - step // 2, x0 + w, mid + step // 2)
        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
