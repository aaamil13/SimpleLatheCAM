"""
Primitive: TurnStock — rapid cleanup of raw stock to a base diameter.

Used as the first cutting operation when the raw bar has scale, casting
skin or irregular surface that would damage a finishing insert.  The
operation takes several radial passes at the roughing step_down to bring
the entire length to a clean, concentric base diameter before precision
feature turning begins.

Profile impact: identical to a Cylinder — advances Z by *length* and sets
the diameter to *target_d*.  The CAM engine uses *category = "Setup"* as
a cue to apply aggressive roughing passes rather than a finishing path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class TurnStockPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "turn_stock"

    @property
    def display_name(self) -> str:
        return "Зачистване"

    @property
    def category(self) -> str:
        return "Setup"

    @property
    def tooltip(self) -> str:
        return (
            "Зачистващ проход — сваля кора/люспи и довежда до базов диаметър.\n"
            "Обикновено е първата режеща операция при суров прът."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("target_d",  "Базов диаметър", "mm",
                      default=48.0, min_val=0.1, max_val=1000.0,
                      tooltip="Диаметърът след зачистването"),
            ParamSpec("length",    "Дължина",        "mm",
                      default=100.0, min_val=0.1, max_val=2000.0),
            ParamSpec("step_down", "Стъпка",         "mm",
                      default=1.0, min_val=0.1, max_val=10.0,
                      tooltip="Радиална дълбочина на всеки проход (за CAM)"),
        ]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        if params["target_d"] > context.stock_d:
            return (
                f"Базовият диаметър {params['target_d']} mm е по-голям от "
                f"заготовката ({context.stock_d} mm)."
            )
        if abs(context.cursor_z) + params["length"] > context.stock_l:
            return "Дължината надвишава наличния материал."
        return None

    def build(self, profile: "LatheProfile", params: dict) -> None:
        profile.add_cylinder(d=params["target_d"], length=params["length"])

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        m   = 6
        x0  = rect.left() + m
        w   = rect.width()  - 2 * m
        mid = rect.center().y()
        step = (rect.height() - 2 * m) // 3

        # Stock outline (dashed, larger)
        pen = QPen(QColor("#78909C"), 1, Qt.DashLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        stock_y = step + step // 3
        painter.drawLine(x0, mid - stock_y, x0 + w, mid - stock_y)
        painter.drawLine(x0, mid + stock_y, x0 + w, mid + stock_y)

        # Cleaned surface (solid, smaller)
        pen.setStyle(Qt.SolidLine)
        pen.setColor(QColor("#80CBC4"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(x0, mid - step, x0 + w, mid - step)
        painter.drawLine(x0, mid + step, x0 + w, mid + step)
        painter.drawLine(x0, mid - step, x0, mid + step)

        # Removal arrows (inward, downward from stock to surface)
        pen.setWidth(1)
        pen.setColor(QColor("#4DB6AC"))
        painter.setPen(pen)
        for frac in (0.25, 0.5, 0.75):
            ax = x0 + int(w * frac)
            painter.drawLine(ax, mid - stock_y, ax, mid - step)
            painter.drawLine(ax, mid - step, ax - 3, mid - step - 4)
            painter.drawLine(ax, mid - step, ax + 3, mid - step - 4)

        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
