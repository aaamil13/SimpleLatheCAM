"""
MainWindow — top-level PySide6 window for the LatheCadCam editor.

Layout
------
  [PrimitiveToolbar — top]
  ┌─────────────────────────────────────────────┐
  │ OperationTree (left) │ LatheCanvas (centre) │ ParamsPanel (right) │
  └─────────────────────────────────────────────┘
  [StatusBar — bottom]

Menus
-----
  File : New, Open, Save, Save As, ── , Export G-code, ── , Quit
  View : Fit View
  Help : About
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QWidget,
)

from cam.gcode_writer import GCodeWriter, WriterConfig
from domain.machine import MachineConfig
from domain.plugin_loader import PrimitivePluginLoader
from domain.recipe import PartRecipe
from domain.tool_library import ToolLibrary
from ui.canvas_2d import LatheCanvas
from ui.editor_model import EditorModel
from ui.operation_tree import OperationTree
from ui.params_panel import ParamsPanel
from ui.primitive_toolbar import PrimitiveToolbar


class MainWindow(QMainWindow):

    def __init__(
        self,
        loader:       PrimitivePluginLoader,
        tool_library: Optional[ToolLibrary] = None,
        machine:      Optional[MachineConfig] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._machine = machine
        self._model   = EditorModel(loader, tool_library, parent=self)
        self._recipe_path: Optional[Path] = None

        self.setWindowTitle("LatheCadCam")
        self.resize(1280, 720)
        self._build_ui()
        self._build_menus()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Toolbar
        self._toolbar = PrimitiveToolbar(self._model.loader, self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

        # Central splitter
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(splitter)

        # Left — operation tree
        self._tree = OperationTree(self._model, self)
        self._tree.setMinimumWidth(220)
        self._tree.setMaximumWidth(320)
        splitter.addWidget(self._tree)

        # Centre — canvas
        self._canvas = LatheCanvas(self)
        if self._machine:
            self._canvas.set_machine(self._machine)
        splitter.addWidget(self._canvas)

        # Right — params panel
        self._params = ParamsPanel(self)
        self._params.setMinimumWidth(200)
        self._params.setMaximumWidth(280)
        splitter.addWidget(self._params)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        # Status bar
        self._status_cursor = QLabel("X: –   Z: –")
        self._status_tool   = QLabel("T: –")
        self._status_err    = QLabel()
        self._status_err.setStyleSheet("color: #EF5350;")
        sb = QStatusBar(self)
        sb.addWidget(self._status_cursor)
        sb.addWidget(QLabel("  |  "))
        sb.addWidget(self._status_tool)
        sb.addPermanentWidget(self._status_err)
        self.setStatusBar(sb)

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # File
        fm = mb.addMenu("&Файл")
        fm.addAction("&Ново",        self._new_recipe,    "Ctrl+N")
        fm.addAction("&Отвори…",     self._open_recipe,   "Ctrl+O")
        fm.addAction("&Запази",      self._save_recipe,   "Ctrl+S")
        fm.addAction("Запази &като…",self._save_recipe_as,"Ctrl+Shift+S")
        fm.addSeparator()
        fm.addAction("&Експорт G-код…", self._export_gcode, "Ctrl+E")
        fm.addSeparator()
        fm.addAction("&Изход", QApplication.quit, "Ctrl+Q")

        # View
        vm = mb.addMenu("&Изглед")
        vm.addAction("&Вмести изглед", self._canvas._fit, "Ctrl+0")

        # Help
        hm = mb.addMenu("&Помощ")
        hm.addAction("&За програмата", self._about)

    def _connect_signals(self) -> None:
        self._model.recipe_changed.connect(self._on_recipe_changed)
        self._model.selection_changed.connect(self._on_selection_changed)
        self._model.error_occurred.connect(self._show_error)
        self._toolbar.primitive_chosen.connect(self._model.add_operation)
        self._params.params_changed.connect(self._model.update_params)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_recipe_changed(self) -> None:
        self._canvas.set_profile(self._model.profile)
        profile = self._model.profile
        self._status_cursor.setText(
            f"X: {profile.cursor_x:.2f} mm   Z: {profile.cursor_z:.2f} mm"
        )
        seq_ops = self._model.recipe.tool_sequences
        if seq_ops:
            t = seq_ops[max(self._model.selected_seq, 0)].tool_id
            self._status_tool.setText(f"T{t:02d}")

    def _on_selection_changed(self, seq_idx: int, op_idx: int) -> None:
        op = self._model.selected_operation()
        if op is None:
            self._params.set_primitive(None)
            return
        plugin = self._model.loader.get(op.primitive_name)
        ctx    = self._model.profile.context()
        self._params.set_primitive(plugin, op.params, ctx)

    def _show_error(self, msg: str) -> None:
        self._status_err.setText(msg)

    # ------------------------------------------------------------------
    # File actions
    # ------------------------------------------------------------------

    def _new_recipe(self) -> None:
        self._model.new_recipe()
        self._recipe_path = None
        self.setWindowTitle("LatheCadCam — New Part")

    def _open_recipe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Отвори рецепта", "", "JSON рецепти (*.json)"
        )
        if path:
            try:
                self._model.load_recipe(path)
                self._recipe_path = Path(path)
                self.setWindowTitle(f"LatheCadCam — {self._recipe_path.name}")
            except Exception as e:
                QMessageBox.critical(self, "Грешка", str(e))

    def _save_recipe(self) -> None:
        if self._recipe_path:
            self._model.save_recipe(self._recipe_path)
        else:
            self._save_recipe_as()

    def _save_recipe_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Запази рецепта", "", "JSON рецепти (*.json)"
        )
        if path:
            self._recipe_path = Path(path)
            self._model.save_recipe(self._recipe_path)

    def _export_gcode(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Експорт G-код", "", "G-код файлове (*.ngc *.nc *.gcode)"
        )
        if not path:
            return
        try:
            writer = GCodeWriter(
                recipe=self._model.recipe,
                profile=self._model.profile,
                tool_library=self._model.tool_library,
                machine=self._machine,
            )
            Path(path).write_text(writer.generate(), encoding="utf-8")
            self.statusBar().showMessage(f"G-код записан: {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Грешка при генериране", str(e))

    def _about(self) -> None:
        QMessageBox.about(
            self, "За LatheCadCam",
            "<b>LatheCadCam</b><br>"
            "Конверсационен CAM редактор за стругове.<br>"
            "Работи самостоятелно или като добавка за LinuxCNC.",
        )
