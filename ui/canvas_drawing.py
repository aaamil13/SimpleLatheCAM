"""
canvas_drawing — standalone drawing helpers for LatheCanvas.

All functions accept a QPainter, domain objects, and a w2s callable
(world-to-screen: (radius, z) -> QPointF).  Keeping these separate
allows canvas_2d.py to stay under the 300-line project limit.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

from PySide6.QtCore import Qt, QPointF, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from domain.machine import MachineConfig
from domain.profile import LatheProfile
from domain.profile_segments import ArcSegment
from domain.tool import Tool

# Type alias
W2S = Callable[[float, float], QPointF]

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------

STOCK_COLOR    = QColor("#546E7A")
PROFILE_COLOR  = QColor("#4FC3F7")
HOVER_COLOR    = QColor("#FFA726")
SELECTED_COLOR = QColor("#66BB6A")
CURSOR_COLOR   = QColor("#FFA726")
AXIS_COLOR     = QColor("#37474F")
LIMIT_COLOR    = QColor("#EF5350")

MATERIAL_FILL: dict[str, QColor] = {
    "Steel":        QColor(96,  125, 139, 80),
    "Stainless":    QColor(144, 164, 174, 80),
    "Aluminium":    QColor(128, 222, 234, 80),
    "Brass/Copper": QColor(255, 213,  79, 80),
    "Cast Iron":    QColor( 69,  90, 100, 80),
    "Titanium":     QColor(206, 147, 216, 80),
}
MATERIAL_FILL_DEFAULT = QColor(96, 125, 139, 70)

# ---------------------------------------------------------------------------
# Drawing functions
# ---------------------------------------------------------------------------

def draw_axis(p: QPainter, profile: LatheProfile, w2s: W2S, canvas_width: int) -> None:
    p.setPen(QPen(AXIS_COLOR, 1, Qt.PenStyle.DashLine))
    left = w2s(0, 0)
    p.drawLine(left, QPointF(canvas_width, left.y()))


def draw_stock(
    p: QPainter,
    profile: LatheProfile,
    machine: Optional[MachineConfig],
    material_category: str,
    w2s: W2S,
) -> None:
    sr = profile.stock_d / 2.0
    sl = profile.stock_l
    tl = w2s( sr,  0.0)
    br = w2s(-sr, -sl)
    rect = QRect(
        int(br.x()), int(tl.y()),
        int(tl.x() - br.x()), int(br.y() - tl.y()),
    )
    p.fillRect(rect, MATERIAL_FILL.get(material_category, MATERIAL_FILL_DEFAULT))
    p.setPen(QPen(STOCK_COLOR, 1, Qt.PenStyle.DashLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(rect)

    if machine and machine.chuck_jaw_depth > 0:
        jd   = machine.chuck_jaw_depth
        j_tl = w2s( sr, -sl)
        j_br = w2s(-sr, -(sl + jd))
        jaw  = QRect(
            int(j_br.x()), int(j_tl.y()),
            int(j_tl.x() - j_br.x()), int(j_br.y() - j_tl.y()),
        )
        p.fillRect(jaw, QColor(239, 83, 80, 60))
        p.setPen(QPen(QColor("#EF5350"), 1, Qt.PenStyle.SolidLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(jaw)


def draw_profile(
    p: QPainter,
    profile: LatheProfile,
    hovered_tag:  Optional[tuple[int, int]],
    selected_tag: Optional[tuple[int, int]],
    w2s: W2S,
) -> None:
    for seg in profile.segments():
        if hovered_tag is not None and seg.tag == hovered_tag:
            pen = QPen(HOVER_COLOR, 3, Qt.PenStyle.SolidLine)
        elif selected_tag is not None and seg.tag == selected_tag:
            pen = QPen(SELECTED_COLOR, 3, Qt.PenStyle.SolidLine)
        else:
            pen = QPen(PROFILE_COLOR, 2, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        pts = seg.points(48) if isinstance(seg, ArcSegment) else seg.points()
        for i in range(len(pts) - 1):
            a  = w2s(pts[i][0],   pts[i][1])
            b  = w2s(pts[i+1][0], pts[i+1][1])
            p.drawLine(a, b)
            a2 = w2s(-pts[i][0],   pts[i][1])
            b2 = w2s(-pts[i+1][0], pts[i+1][1])
            p.drawLine(a2, b2)


def draw_cursor(p: QPainter, profile: LatheProfile, w2s: W2S) -> None:
    pt = w2s(profile.cursor_r, profile.cursor_z)
    p.setPen(QPen(CURSOR_COLOR, 1, Qt.PenStyle.SolidLine))
    size = 8
    p.drawLine(int(pt.x()) - size, int(pt.y()), int(pt.x()) + size, int(pt.y()))
    p.drawLine(int(pt.x()), int(pt.y()) - size, int(pt.x()), int(pt.y()) + size)


def draw_tool(p: QPainter, tool: Tool, tip: QPointF, scale: float) -> None:
    """
    Draw the ISO 1832 insert + holder at the screen cursor position *tip*.

    Geometry
    --------
    The insert is a parallelogram with the nose at *tip*.
    κr (approach_angle) orients the leading edge from the workpiece axis.
    The included cutting angle determines the insert shape width.
    The holder shank is drawn as a rectangle behind the insert body.
    """
    kappa   = math.radians(tool.holder.approach_angle)
    phi     = math.radians(tool.insert.cutting_angle)
    ic_px   = max(tool.insert.ic_size * scale, 8.0)
    tx, ty  = tip.x(), tip.y()

    # Screen-space angle of the leading edge from +X axis (math CCW, screen Y-down)
    # κr = 90° → lead = π/2 (straight up from tip) — perpendicular to Z axis
    lead  = math.pi - kappa
    trail = lead - phi   # trailing edge is phi radians clockwise

    def pt(angle: float) -> QPointF:
        return QPointF(tx + ic_px * math.cos(angle),
                       ty - ic_px * math.sin(angle))

    p1 = QPointF(tx, ty)   # nose
    p2 = pt(lead)           # leading edge end
    p4 = pt(trail)          # trailing edge end
    p3 = QPointF(p2.x() + p4.x() - tx, p2.y() + p4.y() - ty)  # parallelogram 4th corner

    # Holder: rectangle extending from the insert base in the shank direction
    base_cx, base_cy = (p2.x() + p3.x()) / 2, (p2.y() + p3.y()) / 2
    sdx, sdy = base_cx - tx, base_cy - ty
    slen = math.hypot(sdx, sdy) or 1.0
    sux, suy = sdx / slen, sdy / slen          # unit shank direction
    pw  = max(tool.holder.shank_h * scale * 0.18, ic_px * 0.35)  # half-width px
    px_perp_x, px_perp_y = -suy, sux           # perpendicular unit
    hlen = ic_px * 2.5
    holder = QPolygonF([
        QPointF(base_cx + px_perp_x * pw,                 base_cy + px_perp_y * pw),
        QPointF(base_cx - px_perp_x * pw,                 base_cy - px_perp_y * pw),
        QPointF(base_cx + sux * hlen - px_perp_x * pw,    base_cy + suy * hlen - px_perp_y * pw),
        QPointF(base_cx + sux * hlen + px_perp_x * pw,    base_cy + suy * hlen + px_perp_y * pw),
    ])

    p.save()
    p.setBrush(QColor("#37474F"))
    p.setPen(QPen(QColor("#546E7A"), 1))
    p.drawPolygon(holder)

    p.setBrush(QColor("#FFD54F"))
    p.setPen(QPen(QColor("#212121"), 1))
    p.drawPolygon(QPolygonF([p1, p2, p3, p4]))

    nose_px = max(tool.insert.nose_radius * scale, 2.5)
    p.setBrush(QColor(239, 83, 80, 180))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(p1, nose_px, nose_px)
    p.restore()


def draw_limits(
    p: QPainter,
    machine: MachineConfig,
    w2s: W2S,
    canvas_width: int,
    canvas_height: int,
) -> None:
    lim = machine.limits
    p.setPen(QPen(LIMIT_COLOR, 1, Qt.PenStyle.DotLine))
    pt_top = w2s(lim.x_max, 0)
    p.drawLine(0, int(pt_top.y()), canvas_width, int(pt_top.y()))
    pt_z = w2s(0, lim.z_min)
    p.drawLine(int(pt_z.x()), 0, int(pt_z.x()), canvas_height)
