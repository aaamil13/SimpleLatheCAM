"""
Primitive: FaceTurn — face the end of the workpiece.

Generates a radial sweep from the stock outer diameter to the centre (D=0),
removing the facing allowance.  Typically the first operation in any recipe.

The facing depth (axial material removed per pass) is controlled by the
'depth' parameter.  Multiple facing passes are handled by repeating the
operation or by the roughing engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class FaceTurnPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "face_turn"

    @property
    def display_name(self) -> str:
        return "Чело"

    @property
    def category(self) -> str:
        return "Setup"

    @property
    def tooltip(self) -> str:
        return (
            "Челно струговане — радиален проход от края до оста.\n"
            "Обикновено е първата операция в рецептата."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("depth", "Дълбочина на лице", "mm",
                      default=1.0, min_val=0.0, max_val=20.0,
                      tooltip="Аксиален слой на снемане (0 = само на Z=0)"),
        ]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        if params["depth"] > context.stock_l * 0.2:
            return (
                f"Дълбочина {params['depth']} mm изглежда прекалено голяма "
                f"спрямо дължината на заготовката ({context.stock_l} mm)."
            )
        return None

    def build(self, profile: "LatheProfile", params: dict) -> None:
        profile.add_face(depth=params["depth"])

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        m   = 6
        x0  = rect.left() + m
        w   = rect.width() - 2 * m
        mid = rect.center().y()
        step = (rect.height() - 2 * m) // 3

        pen = QPen(QColor("#4DD0E1"), 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Stock face (vertical line on right)
        face_x = x0 + w
        painter.drawLine(face_x, mid - step, face_x, mid + step)

        # Tool arrow moving left (radial facing direction)
        arrow_y = mid - step // 2
        painter.drawLine(face_x, arrow_y, x0 + w // 3, arrow_y)
        painter.drawLine(x0 + w // 3, arrow_y,
                         x0 + w // 3 + 6, arrow_y - 5)
        painter.drawLine(x0 + w // 3, arrow_y,
                         x0 + w // 3 + 6, arrow_y + 5)

        # Second pass arrow (lower)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        arrow_y2 = mid + step // 2
        painter.drawLine(face_x, arrow_y2, x0 + w // 3, arrow_y2)

        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
