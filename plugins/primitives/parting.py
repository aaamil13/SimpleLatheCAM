"""
Primitive: Parting — cut-off operation with chip-breaking modes.

Chip breaking modes
-------------------
  none         — continuous feed to x_target (simple cut-off).
  peck         — plunge peck_depth, retract retract_amount, repeat.
                 Blade stays near the groove (minimal retract).
  full_retract — plunge peck_depth, retract fully to safe_x, re-enter.
                 Best chip control for difficult materials.

The GCodeWriter recognises this primitive by name and emits the
appropriate G-code sequence instead of a plain G1 line.

Profile impact: records a radial line from the surface to x_target.
The cursor X is updated to x_target; Z does not change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile

# Chip break mode constants (stored as float in params for JSON simplicity)
MODE_NONE         = 0.0
MODE_PECK         = 1.0
MODE_FULL_RETRACT = 2.0


class PartingPrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "parting"

    @property
    def display_name(self) -> str:
        return "Отрязване"

    @property
    def category(self) -> str:
        return "Turning"

    @property
    def tooltip(self) -> str:
        return (
            "Отрязване (parting off) с избор на режим за прекъсване на\n"
            "стружката: непрекъснато, прекъсване (peck) или пълно изтегляне."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("x_target",       "Краен диаметър",   "mm",
                      default=0.0,  min_val=0.0,   max_val=500.0,
                      tooltip="0 = пълно отрязване до оста"),
            ParamSpec("chip_break_mode", "Режим прекъсване", "",
                      default=MODE_NONE, min_val=0.0, max_val=2.0,
                      tooltip="0=непрекъснато  1=peck  2=пълно изтегляне"),
            ParamSpec("peck_depth",     "Дълбочина стъпка",  "mm",
                      default=2.0,  min_val=0.1,   max_val=20.0,
                      tooltip="Радиална дълбочина на всяко потапяне (режими 1 и 2)"),
            ParamSpec("retract_amount", "Изтегляне (peck)",  "mm",
                      default=0.5,  min_val=0.1,   max_val=10.0,
                      tooltip="Изтегляне след всяко потапяне (само режим 1)"),
            ParamSpec("safe_x",         "Безопасен X",       "mm",
                      default=60.0, min_val=0.0,   max_val=600.0,
                      tooltip="Диаметър за пълно изтегляне (само режим 2)"),
        ]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        if params["x_target"] >= context.cursor_x:
            return (
                f"Краен диаметър {params['x_target']} mm е >= текущ "
                f"диаметър {context.cursor_x:.1f} mm — няма какво да се реже."
            )
        mode = round(params["chip_break_mode"])
        if mode in (1, 2) and params["peck_depth"] <= 0:
            return "Дълбочината на стъпката трябва да е > 0 при активен режим."
        if mode == 2 and params["safe_x"] <= context.cursor_x:
            return (
                f"Безопасният X {params['safe_x']} mm трябва да е "
                f"> текущия диаметър {context.cursor_x:.1f} mm."
            )
        return None

    def build(self, profile: "LatheProfile", params: dict) -> None:
        # Record the radial cut in the profile geometry.
        # The GCodeWriter handles the actual chip-break G-code sequence.
        profile.add_line_to(d=params["x_target"], z=profile.cursor_z)

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        m   = 6
        x0  = rect.left() + m
        w   = rect.width() - 2 * m
        mid = rect.center().y()
        step = (rect.height() - 2 * m) // 3

        pen = QPen(QColor("#EF5350"), 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Workpiece cross-section (left part)
        cut_x = x0 + w * 2 // 3
        painter.drawLine(x0,    mid - step, cut_x, mid - step)
        painter.drawLine(x0,    mid + step, cut_x, mid + step)
        painter.drawLine(x0,    mid - step, x0,    mid + step)

        # Parting blade (narrow vertical rectangle)
        blade_half = max(2, w // 12)
        pen.setColor(QColor("#B71C1C"))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawLine(cut_x, mid - step, cut_x, mid + step)

        # Downward arrow indicating plunge
        pen.setWidth(1)
        pen.setColor(QColor("#EF5350"))
        painter.setPen(pen)
        arr_x = cut_x + w // 6
        painter.drawLine(arr_x, mid - step, arr_x, mid)
        painter.drawLine(arr_x, mid, arr_x - 4, mid - 5)
        painter.drawLine(arr_x, mid, arr_x + 4, mid - 5)

        # Centre axis
        pen.setStyle(Qt.DotLine)
        pen.setColor(QColor("#546E7A"))
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)

        painter.restore()
