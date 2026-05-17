"""
Primitive: ManualSpindle — pause for a manual spindle operation.

Used when the operator needs to perform manual work (centering, hand
drilling, reaming) with the spindle running at a set RPM.

G-code output (handled by GCodeWriter):
  G97 S{rpm} M3   ; start spindle at fixed RPM
  M0              ; program stop — operator performs manual work
  M5              ; stop spindle

Profile impact: None — no geometry change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class ManualSpindlePrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "manual_spindle"

    @property
    def display_name(self) -> str:
        return "Ръчна операция"

    @property
    def category(self) -> str:
        return "Drilling"

    @property
    def tooltip(self) -> str:
        return (
            "Пауза за ръчна операция — шпинделът се стартира,\n"
            "програмата спира (M0) за ръчно пробиване / центриране."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec(
                "spindle_rpm", "Обороти", "об/мин",
                default=500.0, min_val=10.0, max_val=5000.0, step=50.0,
                tooltip="Обороти на шпиндела по време на ръчната операция",
            ),
        ]

    def build(self, profile: "LatheProfile", params: dict) -> None:
        pass  # No geometry; GCodeWriter emits G97/M3/M0 for this primitive.

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        cx = rect.center().x()
        cy = rect.center().y()
        r  = min(rect.width(), rect.height()) // 2 - 7

        # Spindle ring
        pen = QPen(QColor("#80DEEA"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Centre dot
        painter.setBrush(QColor("#80DEEA"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - 3, cy - 3, 6, 6)

        # Rotation arc (top) indicating spindle motion
        pen2 = QPen(QColor("#4DD0E1"), 2, Qt.PenStyle.SolidLine)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        r2 = r + 5
        painter.drawArc(cx - r2, cy - r2, r2 * 2, r2 * 2, 30 * 16, 120 * 16)

        # Pause indicator — two vertical bars at the bottom
        pen3 = QPen(QColor("#80DEEA"), 2, Qt.PenStyle.SolidLine)
        pen3.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen3)
        bar_y1 = cy + r // 2
        bar_y2 = cy + r
        painter.drawLine(cx - 4, bar_y1, cx - 4, bar_y2)
        painter.drawLine(cx + 4, bar_y1, cx + 4, bar_y2)

        painter.restore()
