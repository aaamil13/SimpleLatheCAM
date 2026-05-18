"""
Primitive: Threading — G76 threading cycle.

Quick-select: pick a standard thread from the drop-down (metric coarse/fine,
UNC, UNF, NPT) and pitch/depth/taper are filled automatically.
Manual mode (std_idx = 0): enter pitch and depth by hand.
Infeed mode: radial (0), leading flank 29.5° (1), trailing flank −29.5° (2).
NPT threads carry the taper rate so gcode_writer inserts the correct I value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext
from domain.thread_data import (
    INFEED_CHOICES, THREAD_CHOICES, get_effective_thread, get_thread,
)

if TYPE_CHECKING:
    from PySide6.QtCore import QRect
    from domain.profile import LatheProfile


_MANUAL_LABEL = "--- Ръчна стъпка ---"
_ALL_THREAD_CHOICES = [_MANUAL_LABEL] + list(THREAD_CHOICES)



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
        return "Нарязване на резба (G76) — метрична, UNC/UNF, NPT, вътрешна или ръчна."

    @property
    def min_segments(self) -> int:
        return 1

    @property
    def params_schema(self) -> list[ParamSpec]:
        n = len(_ALL_THREAD_CHOICES) - 1
        return [
            ParamSpec("std_idx", "Тип резба", "", 0, 0, n,
                      tooltip="Стандартна резба или ръчна стъпка",
                      choices=_ALL_THREAD_CHOICES),
            ParamSpec("pitch",       "Стъпка",        "mm",
                      default=1.5,  min_val=0.1,  max_val=10.0,  step=0.25,
                      tooltip="Стъпка mm/обр — само при ръчен режим"),
            ParamSpec("depth",       "Дълбочина",      "mm",
                      default=0.0,  min_val=0.0,  max_val=10.0,  step=0.05,
                      tooltip="Пълна дълбочина (0 = авто 0.6495×стъпка; само ръчен)"),
            ParamSpec("infeed_mode", "Подаване",       "", 1, 0, 2,
                      tooltip="Режим на подаване — радиален / водещ фланг / следящ фланг",
                      choices=list(INFEED_CHOICES)),
            ParamSpec("length_z",    "Дължина",        "mm",
                      default=20.0, min_val=1.0,  max_val=300.0,
                      tooltip="Аксиална дължина на нарязването"),
            ParamSpec("z_offset",    "Z отм.",         "mm",
                      default=0.0,  min_val=-300.0, max_val=0.0,
                      tooltip="Отместване от текущия cursor (0 = от тук)"),
            ParamSpec("first_pass",  "1-ви проход",    "mm",
                      default=0.3,  min_val=0.05, max_val=2.0,   step=0.05,
                      tooltip="Дълбочина на първия проход (радиус)"),
            ParamSpec("spring_passes", "Пружинни",     "",
                      default=1.0,  min_val=0.0,  max_val=5.0,   step=1.0,
                      tooltip="Брой пружинни (чистови) проходи без подаване"),
        ]

    # ------------------------------------------------------------------
    # Auto-fill on combo change
    # ------------------------------------------------------------------

    def on_param_changed(self, name: str, params: dict) -> dict:
        """When std_idx changes to a standard thread, auto-fill pitch and depth."""
        if name != "std_idx":
            return params
        idx = int(round(params.get("std_idx", 0)))
        if idx == 0:
            return params          # manual — keep current values
        spec = get_thread(idx - 1)
        updated = dict(params)
        updated["pitch"] = spec.pitch_mm
        updated["depth"] = spec.depth_mm
        return updated

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        pitch, depth, _ = get_effective_thread(params)
        if pitch <= 0:
            return "Стъпката трябва да е > 0 mm."
        first_p = params.get("first_pass", 0.3)
        if first_p >= depth:
            return (
                f"Първият проход ({first_p:.3f} mm) трябва да е по-малък от "
                f"пълната дълбочина ({depth:.3f} mm)."
            )
        z_start = context.cursor_z + params.get("z_offset", 0.0)
        z_end   = z_start - params.get("length_z", 20.0)
        if z_end < -context.stock_l:
            return "Резбата излиза извън дължината на заготовката."
        return None

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def build(self, profile: "LatheProfile", params: dict) -> None:
        """Record a horizontal segment spanning the thread zone.

        Threading does not change the nominal surface diameter.
        """
        z_start = profile.cursor_z + params.get("z_offset", 0.0)
        z_end   = z_start - params.get("length_z", 20.0)
        cur_d   = profile.cursor_x
        if abs(params.get("z_offset", 0.0)) > 1e-6:
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

        tooth_h = max(h4 // 2, 3)
        x = x0
        while x + step <= x0 + w:
            mx = x + step // 2
            painter.drawLine(x, mid - h4, mx, mid - h4 - tooth_h)
            painter.drawLine(mx, mid - h4 - tooth_h, x + step, mid - h4)
            painter.drawLine(x, mid + h4, mx, mid + h4 + tooth_h)
            painter.drawLine(mx, mid + h4 + tooth_h, x + step, mid + h4)
            x += step

        pen.setStyle(Qt.PenStyle.DotLine)
        pen.setColor(QColor("#546E7A"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(x0, mid, x0 + w, mid)
        painter.restore()
