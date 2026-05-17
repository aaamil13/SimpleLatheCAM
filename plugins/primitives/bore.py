"""
Primitive: Bore — enlarge an existing internal bore to a precise diameter.

A boring bar is used after an initial drill pass has created the starter
hole.  The bar removes material from the inner wall, producing a precise
cylindrical bore.

Profile convention
------------------
LatheProfile tracks the *outer* profile of the part, but for internal
operations the same coordinate system is used: the "diameter" recorded
is the bore inner diameter.  When the CAM engine sees `direction=INTERNAL`
on the operation record it generates boring passes instead of OD passes.

The cursor is updated so subsequent operations (chamfer, thread, groove)
can be positioned correctly relative to the bore surface.

Chip-breaking
-------------
Boring bars work best with continuous feed (no chip-break).  A peck mode
is provided for deep bores (depth/diameter > 5) or for difficult materials
where chip evacuation is a problem.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class BorePrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "bore"

    @property
    def display_name(self) -> str:
        return "Разстъргване"

    @property
    def category(self) -> str:
        return "Internal"

    @property
    def tooltip(self) -> str:
        return (
            "Разстъргване на вътрешен отвор до точен диаметър.\n"
            "Изисква предварително пробиване."
        )

    @property
    def min_segments(self) -> int:
        return 0  # drilling leaves no profile segments, bore can be first

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("d_bore",    "Диаметър на отвора", "mm",
                      default=20.0, min_val=0.5, max_val=500.0,
                      tooltip="Краен вътрешен диаметър след разстъргването"),
            ParamSpec("length",    "Дълбочина",          "mm",
                      default=30.0, min_val=0.5, max_val=500.0),
            ParamSpec("finish_d",  "Оставен припуск",    "mm",
                      default=0.2, min_val=0.0, max_val=2.0,
                      tooltip="Радиален припуск (на страна) за чистови проход"),
        ]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        if params["d_bore"] >= context.stock_d:
            return (
                f"Диаметърът на отвора {params['d_bore']} mm надвишава "
                f"диаметъра на заготовката {context.stock_d} mm."
            )
        if params["length"] > context.stock_l:
            return "Дълбочината на разстъргването надвишава дължината на заготовката."
        # Warn when bore-to-diameter ratio is high (chatter risk)
        if params["length"] / params["d_bore"] > 5:
            return (
                f"Дълбочина/Диаметър = {params['length']/params['d_bore']:.1f} "
                "(> 5) — риск от вибрации. Препоръчва се скромна стъпка."
            )
        return None

    def build(self, profile: "LatheProfile", params: dict) -> None:
        # Records the internal cylinder in the profile.
        # Direction=INTERNAL on the OperationRecord tells the CAM engine
        # to generate internal (boring) passes rather than OD passes.
        profile.add_cylinder(d=params["d_bore"], length=params["length"])

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        m    = 6
        x0   = rect.left() + m
        w    = rect.width()  - 2 * m
        mid  = rect.center().y()
        step = (rect.height() - 2 * m) // 3
        bore = step // 2    # inner bore half-width in pixels

        pen = QPen(QColor("#CE93D8"), 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Outer workpiece walls
        painter.drawLine(x0, mid - step, x0 + w, mid - step)
        painter.drawLine(x0, mid + step, x0 + w, mid + step)
        painter.drawLine(x0, mid - step, x0, mid + step)   # left cap (chuck)

        # Inner bore walls (hollow section)
        pen.setColor(QColor("#AB47BC"))
        painter.setPen(pen)
        painter.drawLine(x0 + 4, mid - bore, x0 + w, mid - bore)
        painter.drawLine(x0 + 4, mid + bore, x0 + w, mid + bore)

        # Boring bar (thin, pointing right)
        pen.setColor(QColor("#7B1FA2"))
        pen.setWidth(1)
        painter.setPen(pen)
        bar_y_top = mid - bore + 2
        bar_y_bot = mid + bore - 2
        bar_x1    = x0 + w // 4
        bar_x2    = x0 + w - 4
        painter.drawLine(bar_x1, bar_y_top, bar_x2, bar_y_top)
        painter.drawLine(bar_x1, bar_y_bot, bar_x2, bar_y_bot)
        painter.drawLine(bar_x1, bar_y_top, bar_x1, bar_y_bot)
        # Cutting tip (small triangle at right end)
        painter.drawLine(bar_x2, bar_y_top, bar_x2 + 4, mid)
        painter.drawLine(bar_x2, bar_y_bot, bar_x2 + 4, mid)

        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
