"""
canvas_3d.py — PyVista 3D revolve visualiser for the turned part.

Shows the LatheProfile revolved 360° around the spindle axis as a
photo-realistic metallic mesh in an interactive PyVista window.

Requirements
------------
  pip install pyvista pyvistaqt   (~150 MB, VTK-based)

When PyVista is not installed (HAS_PYVISTA = False) the window shows a
plain text placeholder so the rest of the application is not affected.

Coordinate mapping
------------------
  LatheProfile  →  PyVista 3D
  r  (radius)   →  X
  0             →  Y  (profile lies in the XZ plane)
  z  (axial)    →  Z  (rotation axis for extrude_rotate)
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from domain.profile import LatheProfile

# ---------------------------------------------------------------------------
# Optional dependency guard
# ---------------------------------------------------------------------------

os.environ.setdefault("QT_API", "pyside6")   # tell QtPy / pyvistaqt which binding to use

try:
    import numpy as np
    import pyvista as pv
    from pyvistaqt import QtInteractor
    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False

_PLACEHOLDER = (
    "3D изглед не е наличен.\n\n"
    "Инсталирайте зависимостите:\n"
    "  pip install pyvista pyvistaqt"
)


# ---------------------------------------------------------------------------
# Canvas3D widget
# ---------------------------------------------------------------------------

class Canvas3D(QWidget):
    """
    Floating 3D viewer for the turned part.

    Call update_3d_model(profile) to refresh the mesh.
    Use show_window() to raise and activate the window.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent, )
        self.setWindowTitle("LatheCadCam — 3D изглед")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_PYVISTA:
            self._plotter = QtInteractor(self)
            self._plotter.set_background("#1A2229")
            self._plotter.add_axes(line_width=2)
            layout.addWidget(self._plotter.interactor)
        else:
            lbl = QLabel(_PLACEHOLDER, self)
            lbl.setStyleSheet("color:#607D8B; font-size:13px;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            self._plotter = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_window(self) -> None:
        """Raise and activate the 3D window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def update_3d_model(self, profile: LatheProfile) -> None:
        """Rebuild the 3D mesh from *profile* and refresh the viewport."""
        if self._plotter is None:
            return
        self._plotter.clear()
        self._build_mesh(profile)
        self._plotter.reset_camera()
        self._plotter.render()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_mesh(self, profile: LatheProfile) -> None:
        polygon = profile.to_polygon(arc_resolution=48)
        if len(polygon) < 2:
            return

        # Profile in XZ plane: (r, 0, z) — X=radius, Z=axial, rotate around Z
        pts = np.array([[r, 0.0, z] for r, z in polygon], dtype=float)
        n   = len(pts)
        cell = np.hstack([[n], np.arange(n)])
        poly = pv.PolyData()
        poly.points = pts
        poly.lines  = cell

        mesh = poly.extrude_rotate(
            resolution=60, angle=360.0,
            rotation_axis=(0.0, 0.0, 1.0),
            capping=True,
        )
        self._plotter.add_mesh(
            mesh,
            color="silver",
            pbr=True, metallic=0.85, roughness=0.25,
            smooth_shading=True,
        )

        # Stock ghost (transparent bounding cylinder)
        stock_r = profile.stock_d / 2.0
        stock_l = abs(profile.stock_l)
        cyl = pv.Cylinder(
            center=(0.0, 0.0, -stock_l / 2.0),
            direction=(0.0, 0.0, 1.0),
            radius=stock_r, height=stock_l,
            resolution=60, capping=False,
        )
        self._plotter.add_mesh(
            cyl, color="#546E7A", opacity=0.12,
            style="surface",
        )
