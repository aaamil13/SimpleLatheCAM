"""
LatheCanvas — 2D cross-section view of the lathe profile.

Coordinate mapping
------------------
  World : radius (mm, ≥0) on Y axis, Z (mm, ≤0) on X axis
  Screen: origin top-left; X increases rightward (= Z decreasing);
          Y increases downward (= radius decreasing)

  screen_x = offset_x + (-world_z) * scale
  screen_y = offset_y - world_r * scale

Features
--------
  - Stock outline (dashed grey rectangle)
  - Profile contour (solid, 2 px)
  - Cursor crosshair at current profile end position
  - Machine soft-limit guides (faint red lines)
  - Zoom with mouse wheel; pan with middle-click drag
  - Auto-fit on first paint
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import (
    QColor, QMouseEvent, QPainter, QPen, QResizeEvent, QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from domain.machine import ChuckSide, MachineConfig
from domain.profile import LatheProfile
from domain.profile_segments import ArcSegment, LineSegment


_STOCK_COLOR   = QColor("#546E7A")
_PROFILE_COLOR = QColor("#4FC3F7")
_CURSOR_COLOR  = QColor("#FFA726")
_AXIS_COLOR    = QColor("#37474F")
_LIMIT_COLOR   = QColor("#EF5350")

# Semi-transparent fill colour per material category
_MATERIAL_FILL: dict[str, QColor] = {
    "Steel":       QColor(96,  125, 139, 80),   # blue-grey
    "Stainless":   QColor(144, 164, 174, 80),   # lighter grey
    "Aluminium":   QColor(128, 222, 234, 80),   # cyan
    "Brass/Copper":QColor(255, 213, 79,  80),   # amber
    "Cast Iron":   QColor(69,  90,  100, 80),   # dark grey
    "Titanium":    QColor(206, 147, 216, 80),   # purple
}
_MATERIAL_FILL_DEFAULT = QColor(96, 125, 139, 70)


class LatheCanvas(QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setMouseTracking(True)

        self._profile:  Optional[LatheProfile]  = None
        self._machine:  Optional[MachineConfig] = None

        self._scale   = 4.0   # px per mm
        self._offset_x = 60.0
        self._offset_y = 120.0
        self._fit_pending = True

        self._pan_origin: Optional[QPoint] = None
        self._pan_ox = self._offset_x
        self._pan_oy = self._offset_y
        self._material_category: str = "Steel"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_profile(self, profile: LatheProfile) -> None:
        self._profile = profile
        self._fit_pending = True
        self.update()

    def set_machine(self, machine: Optional[MachineConfig]) -> None:
        self._machine = machine
        self.update()

    def set_material_category(self, category: str) -> None:
        self._material_category = category
        self.update()

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    @property
    def _z_sign(self) -> float:
        """+1 for left chuck (face on right edge), -1 for right chuck (face on left)."""
        if self._machine and self._machine.chuck_side == ChuckSide.RIGHT:
            return 1.0
        return -1.0   # default: left chuck, Z=0 on right, negative Z to the left

    def _w2s(self, r: float, z: float) -> QPointF:
        """World (r, z) → screen (px, py)."""
        return QPointF(
            self._offset_x + self._z_sign * (-z) * self._scale,
            self._offset_y - r * self._scale,
        )

    def _fit(self) -> None:
        if self._profile is None:
            return
        stock_r = self._profile.stock_d / 2.0
        stock_l = self._profile.stock_l
        margin  = 20  # px
        w       = max(self.width()  - 2 * margin, 1)
        h       = max(self.height() - 2 * margin, 1)
        scale_z = w / max(stock_l, 1)
        scale_r = h / max(stock_r * 2.2, 1)
        self._scale = max(min(scale_z, scale_r), 0.1)
        if self._z_sign > 0:
            # right chuck: face (Z=0) on the left, chuck on the right
            self._offset_x = margin
        else:
            # left chuck: face (Z=0) on the right
            self._offset_x = self.width() - margin - stock_l * self._scale
        self._offset_y = self.height() / 2.0 + stock_r * self._scale * 0.5
        self._fit_pending = False

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor("#1E272E"))

            if self._profile is None:
                p.setPen(QColor("#546E7A"))
                p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "Няма профил")
                return

            if self._fit_pending:
                self._fit()

            self._draw_axis(p)
            self._draw_stock(p)
            if self._machine:
                self._draw_limits(p)
            self._draw_profile(p)
            self._draw_cursor(p)
        finally:
            p.end()

    def _draw_axis(self, p: QPainter) -> None:
        pen = QPen(_AXIS_COLOR, 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        left  = self._w2s(0, 0)
        right = self._w2s(0, -self._profile.stock_l if self._profile else -200)
        p.drawLine(left, QPointF(self.width(), left.y()))

    def _draw_stock(self, p: QPainter) -> None:
        if self._profile is None:
            return
        sr = self._profile.stock_d / 2.0
        sl = self._profile.stock_l
        tl = self._w2s(sr,  0.0)
        br = self._w2s(-sr, -sl)
        rect = QRect(
            int(br.x()), int(tl.y()),
            int(tl.x() - br.x()), int(br.y() - tl.y()),
        )

        # Semi-transparent fill coloured by material category
        fill = _MATERIAL_FILL.get(self._material_category, _MATERIAL_FILL_DEFAULT)
        p.fillRect(rect, fill)

        # Dashed outline
        p.setPen(QPen(_STOCK_COLOR, 1, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

        # Chuck jaw zone (red region at the clamped end)
        if self._machine and self._machine.chuck_jaw_depth > 0:
            jd  = self._machine.chuck_jaw_depth
            # Chuck is at Z = -sl; jaws extend a further jd in -Z
            j_tl = self._w2s(sr,  -sl)
            j_br = self._w2s(-sr, -(sl + jd))
            jaw_rect = QRect(
                int(j_br.x()), int(j_tl.y()),
                int(j_tl.x() - j_br.x()), int(j_br.y() - j_tl.y()),
            )
            p.fillRect(jaw_rect, QColor(239, 83, 80, 60))
            p.setPen(QPen(QColor("#EF5350"), 1, Qt.PenStyle.SolidLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(jaw_rect)

    def _draw_profile(self, p: QPainter) -> None:
        if self._profile is None:
            return
        pen = QPen(_PROFILE_COLOR, 2, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        for seg in self._profile.segments():
            if isinstance(seg, LineSegment):
                a = self._w2s(seg.x0, seg.z0)
                b = self._w2s(seg.x1, seg.z1)
                p.drawLine(a, b)
                # Mirror below centreline (visual symmetry)
                a2 = self._w2s(-seg.x0, seg.z0)
                b2 = self._w2s(-seg.x1, seg.z1)
                p.drawLine(a2, b2)
            elif isinstance(seg, ArcSegment):
                pts = seg.points(resolution=48)
                for i in range(len(pts) - 1):
                    a = self._w2s(pts[i][0],   pts[i][1])
                    b = self._w2s(pts[i+1][0], pts[i+1][1])
                    p.drawLine(a, b)
                    a2 = self._w2s(-pts[i][0],   pts[i][1])
                    b2 = self._w2s(-pts[i+1][0], pts[i+1][1])
                    p.drawLine(a2, b2)

    def _draw_cursor(self, p: QPainter) -> None:
        if self._profile is None:
            return
        r  = self._profile._cursor_r
        z  = self._profile.cursor_z
        pt = self._w2s(r, z)
        pen = QPen(_CURSOR_COLOR, 1, Qt.PenStyle.SolidLine)
        p.setPen(pen)
        size = 8
        p.drawLine(int(pt.x()) - size, int(pt.y()),
                   int(pt.x()) + size, int(pt.y()))
        p.drawLine(int(pt.x()), int(pt.y()) - size,
                   int(pt.x()), int(pt.y()) + size)

    def _draw_limits(self, p: QPainter) -> None:
        if self._machine is None:
            return
        lim = self._machine.limits
        pen = QPen(_LIMIT_COLOR, 1, Qt.PenStyle.DotLine)
        p.setPen(pen)
        # X max (radial limit)
        pt_top = self._w2s(lim.x_max, 0)
        p.drawLine(0, int(pt_top.y()), self.width(), int(pt_top.y()))
        # Z min (axial limit)
        pt_z = self._w2s(0, lim.z_min)
        p.drawLine(int(pt_z.x()), 0, int(pt_z.x()), self.height())

    # ------------------------------------------------------------------
    # Zoom / pan
    # ------------------------------------------------------------------

    def wheelEvent(self, e: QWheelEvent) -> None:
        factor = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        mx, my = e.position().x(), e.position().y()
        self._offset_x = mx + (self._offset_x - mx) * factor
        self._offset_y = my + (self._offset_y - my) * factor
        self._scale   *= factor
        self.update()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = e.pos()
            self._pan_ox = self._offset_x
            self._pan_oy = self._offset_y

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._pan_origin is not None:
            dx = e.pos().x() - self._pan_origin.x()
            dy = e.pos().y() - self._pan_origin.y()
            self._offset_x = self._pan_ox + dx
            self._offset_y = self._pan_oy + dy
            self.update()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = None

    def resizeEvent(self, e: QResizeEvent) -> None:
        self._fit_pending = True
        super().resizeEvent(e)
