"""
Primitive: Drill — axial peck-drilling cycle along the spindle axis.

Typically performed with a twist drill held in the tailstock or turret,
drilling along Z from the face inward.  Required before any boring
operation — creates the starter hole.

Chip-breaking modes (stored as float for JSON compatibility):
  0 — G82  straight drill with dwell at the bottom
  1 — G83  full retract peck cycle (best chip control, standard for steels)

Profile impact: None — drilling does not change the external contour
that LatheProfile tracks.  The G-code writer emits G82/G83 based on
the operation record; the boring bar then takes over for the exact bore.

Notes
-----
  - The drill diameter must match a real tool in the ToolLibrary.
  - `z_start` defaults to 0 (face datum); use a positive value when the
    tailstock approaches from a retracted position.
  - `peck_depth` is ignored in G82 (dwell-only) mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile

MODE_DWELL = 0.0   # G82
MODE_PECK  = 1.0   # G83


class DrillPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "drill"

    @property
    def display_name(self) -> str:
        return "Пробиване"

    @property
    def category(self) -> str:
        return "Drilling"

    @property
    def tooltip(self) -> str:
        return (
            "Аксиално пробиване по оста на въртене (G82/G83).\n"
            "Подготвя вътрешен отвор за последващо разстъргване."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("diameter",   "Диаметър на свредло", "mm",
                      default=10.0, min_val=0.5, max_val=80.0),
            ParamSpec("depth",      "Дълбочина",           "mm",
                      default=30.0, min_val=1.0, max_val=500.0,
                      tooltip="Аксиална дълбочина на отвора (от лицето)"),
            ParamSpec("peck_depth", "Стъпка (peck)",       "mm",
                      default=5.0, min_val=0.5, max_val=50.0,
                      tooltip="Дълбочина на всяко потапяне при G83"),
            ParamSpec("dwell",      "Задържане (G82)",     "s",
                      default=0.0, min_val=0.0, max_val=10.0,
                      tooltip="Секунди задържане на дъното (само G82)"),
            ParamSpec("mode",       "Режим (0=G82 1=G83)", "",
                      default=MODE_PECK, min_val=0.0, max_val=1.0,
                      tooltip="0 = G82 (dwell), 1 = G83 (peck retract)"),
        ]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        if params["diameter"] >= context.stock_d:
            return (
                f"Диаметърът на свредлото {params['diameter']} mm е >= "
                f"диаметъра на заготовката {context.stock_d} mm."
            )
        if params["depth"] > context.stock_l:
            return "Дълбочината на пробиването надвишава дължината на заготовката."
        return None

    def build(self, profile: "LatheProfile", params: dict) -> None:
        pass  # Drilling does not add geometry to the external profile.
              # GCodeWriter emits G82/G83 when it encounters this primitive name.

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        m    = 6
        x0   = rect.left() + m
        w    = rect.width()  - 2 * m
        mid  = rect.center().y()
        step = (rect.height() - 2 * m) // 3
        half = w // 5    # drill half-width

        pen = QPen(QColor("#FF8A65"), 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Workpiece right wall (stock end face)
        wp_x = x0 + w
        painter.drawLine(wp_x, mid - step, wp_x, mid + step)

        # Drill body (rectangle moving left to right)
        drill_tip_x = wp_x - w // 2
        painter.drawLine(x0, mid - half, drill_tip_x, mid - half)
        painter.drawLine(x0, mid + half, drill_tip_x, mid + half)
        painter.drawLine(x0, mid - half, x0, mid + half)

        # Drill point (triangle / V tip)
        painter.drawLine(drill_tip_x, mid - half, wp_x - w // 8, mid)
        painter.drawLine(drill_tip_x, mid + half, wp_x - w // 8, mid)

        # Feed arrow (rightward)
        pen.setColor(QColor("#FF7043"))
        pen.setWidth(1)
        painter.setPen(pen)
        arr_y = mid - step + step // 2
        ax    = x0 + w // 3
        painter.drawLine(ax, arr_y, ax + w // 4, arr_y)
        painter.drawLine(ax + w // 4, arr_y, ax + w // 4 - 4, arr_y - 4)
        painter.drawLine(ax + w // 4, arr_y, ax + w // 4 - 4, arr_y + 4)

        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
