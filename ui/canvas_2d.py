"""
LatheCanvas — interactive 2D cross-section view of the lathe profile.

Coordinate mapping
------------------
  World : radius (mm, ≥0) on Y axis, Z (mm, ≤0) on X axis
  Screen: origin top-left; X increases rightward (= Z decreasing);
          Y increases downward (= radius decreasing)

Interactions
------------
  Wheel          — zoom centred on cursor
  Middle-drag    — pan
  Left-click     — select the nearest operation segment
  Right-click    — context menu (delete, insert before/after, stock settings)
  Hover          — nearest segment highlighted in orange

Signals emitted
---------------
  segment_selected(seq_idx, op_idx)
  request_delete(seq_idx, op_idx)
  request_insert(seq_idx, op_idx, direction_str, primitive_name)
  request_stock_edit()
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QMenu, QWidget

from domain.machine import ChuckSide, MachineConfig
from domain.profile import LatheProfile
from domain.profile_segments import ArcSegment

from domain.tool import Tool
from ui.canvas_drawing import (
    draw_axis, draw_cursor, draw_limits, draw_profile, draw_stock, draw_tool,
)

_MENU_STYLE = (
    "QMenu { background:#263238; color:#ECEFF1; border:1px solid #37474F; }"
    "QMenu::item:selected { background:#37474F; }"
    "QMenu::separator { height:1px; background:#37474F; margin:4px 0; }"
)


class LatheCanvas(QWidget):

    segment_selected  = Signal(int, int)           # seq_idx, op_idx
    request_delete    = Signal(int, int)            # seq_idx, op_idx
    request_insert    = Signal(int, int, str, str)  # seq_idx, op_idx, dir, primitive
    request_stock_edit = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setMouseTracking(True)

        self._profile:  Optional[LatheProfile]  = None
        self._machine:  Optional[MachineConfig] = None

        self._scale    = 4.0
        self._offset_x = 60.0
        self._offset_y = 120.0
        self._fit_pending = True

        self._pan_origin: Optional[QPoint] = None
        self._pan_ox = self._offset_x
        self._pan_oy = self._offset_y

        self._material_category: str = "Steel"
        self._hovered_tag:  Optional[tuple[int, int]] = None
        self._selected_tag: Optional[tuple[int, int]] = None
        self._active_tool:  Optional[Tool] = None
        self._primitives: list[tuple[str, str]] = []  # (name, display_name)

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

    def set_primitives(self, primitives: list[tuple[str, str]]) -> None:
        """Pass [(name, display_name), ...] from the plugin loader."""
        self._primitives = primitives

    def set_active_tool(self, tool: Optional[Tool]) -> None:
        self._active_tool = tool
        self.update()

    def set_selected_tag(self, seq_idx: int, op_idx: int) -> None:
        self._selected_tag = (seq_idx, op_idx) if op_idx >= 0 else None
        self.update()

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    @property
    def _z_sign(self) -> float:
        if self._machine and self._machine.chuck_side == ChuckSide.RIGHT:
            return 1.0
        return -1.0

    def _w2s(self, r: float, z: float) -> QPointF:
        return QPointF(
            self._offset_x + self._z_sign * (-z) * self._scale,
            self._offset_y - r * self._scale,
        )

    def _fit(self) -> None:
        if self._profile is None:
            return
        stock_r = self._profile.stock_d / 2.0
        stock_l = self._profile.stock_l
        margin  = 20
        w = max(self.width()  - 2 * margin, 1)
        h = max(self.height() - 2 * margin, 1)
        scale_z = w / max(stock_l, 1)
        scale_r = h / max(stock_r * 2.2, 1)
        self._scale = max(min(scale_z, scale_r), 0.1)
        if self._z_sign > 0:
            self._offset_x = margin
        else:
            self._offset_x = self.width() - margin - stock_l * self._scale
        self._offset_y = self.height() / 2.0 + stock_r * self._scale * 0.5
        self._fit_pending = False

    # ------------------------------------------------------------------
    # Paint — delegates to canvas_drawing helpers
    # ------------------------------------------------------------------

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor("#1E272E"))
            if self._profile is None:
                p.setPen(QColor("#546E7A"))
                p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Няма профил")
                return
            if self._fit_pending:
                self._fit()
            draw_axis(p, self._profile, self._w2s, self.width())
            draw_stock(p, self._profile, self._machine, self._material_category, self._w2s)
            if self._machine:
                draw_limits(p, self._machine, self._w2s, self.width(), self.height())
            draw_profile(p, self._profile, self._hovered_tag, self._selected_tag, self._w2s)
            draw_cursor(p, self._profile, self._w2s)
            if self._active_tool is not None:
                tip = self._w2s(self._profile.cursor_r, self._profile.cursor_z)
                draw_tool(p, self._active_tool, tip, self._scale)
        finally:
            p.end()

    # ------------------------------------------------------------------
    # Hit-testing
    # ------------------------------------------------------------------

    @staticmethod
    def _dist_to_seg(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
        L2 = (bx - ax) ** 2 + (by - ay) ** 2
        if L2 == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / L2))
        return math.hypot(px - ax - t * (bx - ax), py - ay - t * (by - ay))

    def _get_tag_at_pos(self, pos) -> Optional[tuple[int, int]]:
        if self._profile is None:
            return None
        px, py = pos.x(), pos.y()
        min_dist, best_tag = 6.0, None
        for seg in self._profile.segments():
            if seg.tag is None:
                continue
            pts = seg.points(16) if isinstance(seg, ArcSegment) else seg.points()
            for i in range(len(pts) - 1):
                p1  = self._w2s( pts[i][0],    pts[i][1])
                p2  = self._w2s( pts[i+1][0],  pts[i+1][1])
                p1m = self._w2s(-pts[i][0],    pts[i][1])
                p2m = self._w2s(-pts[i+1][0],  pts[i+1][1])
                for a, b in ((p1, p2), (p1m, p2m)):
                    d = self._dist_to_seg(px, py, a.x(), a.y(), b.x(), b.y())
                    if d < min_dist:
                        min_dist, best_tag = d, seg.tag
        return best_tag

    # ------------------------------------------------------------------
    # Mouse events
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
        elif e.button() == Qt.MouseButton.LeftButton:
            tag = self._get_tag_at_pos(e.pos())
            if tag is not None:
                self._selected_tag = tag
                self.segment_selected.emit(*tag)
                self.update()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._pan_origin is not None:
            dx = e.pos().x() - self._pan_origin.x()
            dy = e.pos().y() - self._pan_origin.y()
            self._offset_x = self._pan_ox + dx
            self._offset_y = self._pan_oy + dy
            self.update()
        else:
            tag = self._get_tag_at_pos(e.pos())
            if tag != self._hovered_tag:
                self._hovered_tag = tag
                self.update()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = None

    def resizeEvent(self, e: QResizeEvent) -> None:
        self._fit_pending = True
        super().resizeEvent(e)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_STYLE)
        tag = self._get_tag_at_pos(event.pos())
        if tag is not None:
            self._selected_tag = tag
            self.segment_selected.emit(*tag)
            self.update()
            si, oi = tag
            menu.addAction("Изтрий операцията").triggered.connect(
                lambda: self.request_delete.emit(si, oi)
            )
            menu.addSeparator()
            self._fill_insert_menu(menu.addMenu("Вмъкни преди…"), si, oi)
            self._fill_insert_menu(menu.addMenu("Вмъкни след…"),  si, oi + 1)
            menu.addSeparator()
        menu.addAction("Заготовка / Материал…").triggered.connect(
            self.request_stock_edit.emit
        )
        menu.exec(event.globalPos())

    def _fill_insert_menu(self, parent: QMenu, si: int, target_oi: int) -> None:
        m_ext = parent.addMenu("Външно")
        m_int = parent.addMenu("Вътрешно")
        for name, display in self._primitives:
            m_ext.addAction(display).triggered.connect(
                lambda _, n=name: self.request_insert.emit(si, target_oi, "external", n)
            )
            m_int.addAction(display).triggered.connect(
                lambda _, n=name: self.request_insert.emit(si, target_oi, "internal", n)
            )
