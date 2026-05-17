"""
Primitive: OperatorMessage — display a message to the operator.

The message text is stored per-language in OperationRecord.extras:
  extras = {"bg": "Завийте детайла", "en": "Clamp the part"}

G-code output (handled by GCodeWriter using AppConfig.operator_language):
  (MSG, <selected language text>)
  M0    ← if require_confirm == 1 (mandatory stop, LinuxCNC waits for CYCLE START)
  [no M0 if require_confirm == 0 — informational only]

Profile impact: None.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont

from domain.primitive_base import LathePrimitive, ParamSpec, ProfileContext

if TYPE_CHECKING:
    from domain.profile import LatheProfile


class OperatorMessagePrimitive(LathePrimitive):

    @property
    def name(self) -> str:
        return "operator_message"

    @property
    def display_name(self) -> str:
        return "Съобщение до оператора"

    @property
    def category(self) -> str:
        return "Setup"

    @property
    def tooltip(self) -> str:
        return (
            "Показва съобщение на оператора.\n"
            "С потвърждение (M0): програмата спира до натискане на CYCLE START.\n"
            "Без потвърждение: само информационен коментар в G-кода."
        )

    @property
    def params_schema(self) -> list[ParamSpec]:
        return [
            ParamSpec(
                "require_confirm", "Изисква потвърждение", "",
                default=1.0, min_val=0.0, max_val=1.0, step=1.0,
                tooltip="1 = програмата спира (M0) и чака оператора;\n"
                        "0 = само коментар в G-кода, изпълнението продължава.",
            ),
        ]

    def build(self, profile: "LatheProfile", params: dict) -> None:
        pass  # No geometry change.

    def draw_icon(self, painter: QPainter, rect: QRect) -> None:
        painter.save()
        cx  = rect.center().x()
        cy  = rect.center().y()
        m   = 6
        r   = min(rect.width(), rect.height()) // 2 - m

        # Speech bubble outline
        pen = QPen(QColor("#FFD54F"), 2, Qt.PenStyle.SolidLine)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Rounded rectangle (bubble body)
        bubble_h = int(r * 1.2)
        bubble_w = int(r * 1.6)
        bx = cx - bubble_w // 2
        by = cy - bubble_h // 2 - r // 4
        painter.drawRoundedRect(bx, by, bubble_w, bubble_h, 6, 6)

        # Tail (triangle at bottom-left)
        tail_pts_x = [bx + bubble_w // 4, bx + bubble_w // 4 - 6, bx + bubble_w // 4 + 4]
        tail_pts_y = [by + bubble_h, by + bubble_h + 8, by + bubble_h]
        for i in range(2):
            painter.drawLine(
                tail_pts_x[i], tail_pts_y[i],
                tail_pts_x[i + 1], tail_pts_y[i + 1],
            )

        # Dots inside bubble (ellipsis … indicating text)
        painter.setBrush(QColor("#FFD54F"))
        painter.setPen(Qt.PenStyle.NoPen)
        dot_y = by + bubble_h // 2
        for dx in (-5, 0, 5):
            painter.drawEllipse(cx + dx - 2, dot_y - 2, 4, 4)

        painter.restore()
