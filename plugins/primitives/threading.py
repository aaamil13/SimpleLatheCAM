"""
Primitive: Threading — generates a G76 threading cycle.

The 2D profile records a horizontal segment at the current surface diameter
spanning the thread length (Z from start to end).  This keeps the contour
geometrically correct — threading does not change the nominal outer diameter.

G-code output (handled by cam/gcode_writer._threading_block):
  Rapid to clearance X, approach Z
  G76 P{pitch} Z{z_end} I{depth_sign} J{first_pass} K{angle} H{spring}

Supports both external (I < 0) and internal (I > 0) threads.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from PySide6.QtCore import QRect
    from domain.profile import LatheProfile


class ThreadingPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "threading"

    @property
    def display_name(self) -> str:
        return "Резба"

    @property
    def category(self) -> str:
        return "Turning"

    @property
    def tooltip(self) -> str:
        return "Нарязване на резба (G76 цикъл) — метрична, UNF или трапецовидна."

    @property
    def min_segments(self) -> int:
        return 1  # Needs an existing cylindrical surface

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("pitch",        "Стъпка",         "mm",
                      default=1.5,  min_val=0.1,  max_val=10.0, step=0.25,
                      tooltip="Стъпка на резбата (mm/обр). Напр.: M6=1.0, M10=1.5, M16=2.0"),
            ParamSpec("length_z",     "Дължина",         "mm",
                      default=20.0, min_val=1.0,  max_val=300.0,
                      tooltip="Аксиална дължина на нарязването"),
            ParamSpec("z_offset",     "Z отм.",          "mm",
                      default=0.0,  min_val=-300.0, max_val=0.0,
                      tooltip="Отместване от текущия cursor (0 = от тук)"),
            ParamSpec("depth",        "Дълбочина",       "mm",
                      default=0.0,  min_val=0.0,  max_val=10.0, step=0.05,
                      tooltip="Пълна дълбочина на профила (0 = авто: 0.6495 × стъпка)"),
            ParamSpec("first_pass",   "1-ви проход",     "mm",
                      default=0.3,  min_val=0.05, max_val=2.0,  step=0.05,
                      tooltip="Дълбочина на първия проход (радиус)"),
            ParamSpec("spring_passes","Пружинни",        "",
                      default=1.0,  min_val=0.0,  max_val=5.0,  step=1.0,
                      tooltip="Брой пружинни (чистови) проходи без подаване"),
            ParamSpec("infeed_angle", "Ъгъл подаване",   "deg",
                      default=29.5, min_val=0.0,  max_val=45.0, step=0.5,
                      tooltip="Ъгъл на подаване — 29.5° за 60°-метрична, 27.5° за трапец"),
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        pitch   = params["pitch"]
        depth   = params["depth"] or 0.6495 * pitch
        first_p = params["first_pass"]
        if first_p >= depth:
            return (
                f"Първият проход ({first_p:.3f} mm) трябва да е по-малък от "
                f"пълната дълбочина ({depth:.3f} mm)."
            )
        z_start = context.cursor_z + params["z_offset"]
        z_end   = z_start - params["length_z"]
        if z_end < -context.stock_l:
            return "Резбата излиза извън дължината на заготовката."
        return None

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def build(self, profile: "LatheProfile", params: dict) -> None:
        """
        Record a horizontal segment spanning the thread zone.
        Threading does not change the nominal surface diameter — the segment
        stays at the current cursor radius so the contour remains correct.
        """
        z_start = profile.cursor_z + params["z_offset"]
        z_end   = z_start - params["length_z"]
        cur_d   = profile.cursor_x  # nominal thread diameter

        if abs(params["z_offset"]) > 1e-6:
            profile.add_line_to(d=cur_d, z=z_start)

        profile.add_line_to(d=cur_d, z=z_end)

    # ------------------------------------------------------------------
    # Icon
    # ------------------------------------------------------------------

    def draw_icon(self, painter: "QPainter", rect: "QRect") -> None:
        painter.save()
        m    = 6
        x0   = rect.left() + m
        w    = rect.width() - 2 * m
        mid  = rect.center().y()
        h4   = (rect.height() - 2 * m) // 4
        step = max(w // 6, 4)

        pen = QPen(QColor("#FFD54F"), 2, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # Thread teeth on both profile lines
        tooth_h = max(h4 // 2, 3)
        x = x0
        while x + step <= x0 + w:
            mx = x + step // 2
            # Upper profile
            painter.drawLine(x, mid - h4, mx, mid - h4 - tooth_h)
            painter.drawLine(mx, mid - h4 - tooth_h, x + step, mid - h4)
            # Lower profile (mirrored)
            painter.drawLine(x, mid + h4, mx, mid + h4 + tooth_h)
            painter.drawLine(mx, mid + h4 + tooth_h, x + step, mid + h4)
            x += step

        # Axis
        pen.setStyle(Qt.PenStyle.DotLine)
        pen.setColor(QColor("#546E7A"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
