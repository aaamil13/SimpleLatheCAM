"""
MiniProfileView — compact 40 px read-only profile thumbnail.

Shows stock outline (dashed) + machined profile (blue) scaled to fit
the available width.  Used inside StepCard to visualise the part state
up to a given operation.

No mouse, no zoom, no tool — pure visualisation.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPointF
from PySide6.QtWidgets import QWidget

from domain.profile import LatheProfile
from domain.profile_segments import ArcSegment

_BG       = QColor("#1A2229")
_STOCK    = QColor("#37474F")
_PROFILE  = QColor("#4FC3F7")


class MiniProfileView(QWidget):
    """
    40-pixel tall profile thumbnail.

    Call set_profile() with the partially-built LatheProfile to refresh.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(40)
        self._profile: Optional[LatheProfile] = None

    def set_profile(self, profile: Optional[LatheProfile]) -> None:
        self._profile = profile
        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), _BG)
            if self._profile is None:
                return

            sr = self._profile.stock_d / 2.0
            sl = self._profile.stock_l
            w  = max(self.width()  - 4, 1)
            h  = max(self.height() - 6, 1)
            scale = min(w / max(sl, 1), h / max(sr * 2.2, 1))
            ox  = 2.0
            oy  = self.height() / 2.0 + sr * scale * 0.5

            def w2s(r: float, z: float) -> QPointF:
                return QPointF(ox + (-z) * scale, oy - r * scale)

            # Stock outline
            tl = w2s( sr,   0.0)
            br = w2s(-sr,  -sl)
            p.setPen(QPen(_STOCK, 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(tl, br))

            # Profile segments (both halves, mirrored)
            pen = QPen(_PROFILE, 1.5, Qt.PenStyle.SolidLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            for seg in self._profile.segments():
                pts = seg.points(16) if isinstance(seg, ArcSegment) else seg.points()
                for i in range(len(pts) - 1):
                    p.drawLine(w2s( pts[i][0],   pts[i][1]),
                               w2s( pts[i+1][0], pts[i+1][1]))
                    p.drawLine(w2s(-pts[i][0],   pts[i][1]),
                               w2s(-pts[i+1][0], pts[i+1][1]))
        finally:
            p.end()
