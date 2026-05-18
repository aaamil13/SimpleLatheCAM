"""
Primitive: Taper — conical step with two definition modes.

Mode 0 (default): define by end diameter D_end and axial length L.
Mode 1:           define by half-angle α (deg) and length L.
                  α > 0 → narrowing (conventional external taper).
                  α < 0 → widening (back taper / relief).

Formula mode 1:  d_end = cursor_x − 2 · L · tan(α)
"""

from __future__ import annotations

import math
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
        return (
            "Конусен стъпал.\n"
            "Режим 0 — по краен диаметър и дължина.\n"
            "Режим 1 — по полу-ъгъл α (°) и дължина."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec("mode",   "Режим (0=⌀ 1=ъгъл)", "",
                      default=0.0, min_val=0.0, max_val=1.0,
                      tooltip="0 = задай краен диаметър; 1 = задай полу-ъгъл"),
            ParamSpec("d_end",  "Краен диаметър",      "mm",
                      default=20.0, min_val=0.0, max_val=1000.0,
                      tooltip="Диаметър в края на конуса (само Режим 0)"),
            ParamSpec("angle",  "Полу-ъгъл α",         "deg",
                      default=15.0, min_val=-89.0, max_val=89.0,
                      tooltip="Ъгъл между конусната повърхност и оста Z (само Режим 1)"),
            ParamSpec("length", "Дължина",              "mm",
                      default=20.0, min_val=0.1, max_val=2000.0),
        ]

    def _resolve_d_end(self, params: dict, cursor_x: float) -> float:
        """Compute the final diameter from params and current cursor."""
        if round(params.get("mode", 0)) == 1:
            return cursor_x - 2.0 * params["length"] * math.tan(
                math.radians(params["angle"])
            )
        return params["d_end"]

    def validate(self, params: dict, context: ProfileContext) -> str | None:
        err = super().validate(params, context)
        if err:
            return err
        d_end = self._resolve_d_end(params, context.cursor_x)
        if d_end < 0:
            return (
                f"Ъгълът {params['angle']:.1f}° и дължина {params['length']} mm "
                "дават отрицателен краен диаметър — намалете ъгъла или дължината."
            )
        if d_end > context.stock_d:
            return (
                f"Краен диаметър {d_end:.2f} mm надвишава "
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
        d_end = self._resolve_d_end(params, profile.cursor_x)
        profile.add_taper(d_end=d_end, length=params["length"])

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
