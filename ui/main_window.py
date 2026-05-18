"""MainWindow — top-level PySide6 window for the LatheCadCam editor."""

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

from cam.gcode_writer import GCodeWriter
from domain.app_config import AppConfig
from domain.machine import MachineConfig
from domain.material import MaterialLibrary
from domain.plugin_loader import PrimitivePluginLoader
from domain.tool import ToolDirection
from domain.tool_library import ToolLibrary
from ui.action_toolbar import ActionToolbar
from ui.canvas_2d import LatheCanvas
from ui.canvas_3d import Canvas3D
from ui.editor_model import EditorModel
from ui.left_sidebar import LeftSidebar
from ui.steps_panel import StepsPanel
from ui.tool_editor import ToolEditor


class MainWindow(QMainWindow):

    def __init__(
        self,
        loader:           PrimitivePluginLoader,
        tool_library:     Optional[ToolLibrary]     = None,
        machine:          Optional[MachineConfig]   = None,
        app_config:       Optional[AppConfig]       = None,
        material_library: Optional[MaterialLibrary] = None,
        driver=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._machine    = machine
        self._app_config = app_config or AppConfig()
        self._driver     = driver
        self._model      = EditorModel(
            loader, tool_library, material_library, parent=self
        )
        self._recipe_path:       Optional[Path] = None
        self._tool_library_path: Optional[Path] = None
        self._canvas3d:          Optional[Canvas3D] = None

        self.setWindowTitle("LatheCadCam")
        self.resize(1400, 800)
        self._build_ui()
        self._build_menus()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Top toolbar
        self._toolbar = ActionToolbar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

        # Central splitter: left | canvas | right
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(splitter)

        # Left sidebar (tabs: primitives + operations)
        self._sidebar = LeftSidebar(self._model, self)
        splitter.addWidget(self._sidebar)

        # Centre — 2D canvas
        self._canvas = LatheCanvas(self)
        if self._machine:
            self._canvas.set_machine(self._machine)
        self._canvas.set_primitives(
            [(p.name, p.display_name) for p in self._model.loader.all()]
        )
        splitter.addWidget(self._canvas)

        # Right — steps panel (accordion)
        self._steps = StepsPanel(self._model, self._machine, self._app_config, self)
        self._steps.setMinimumWidth(220)
        self._steps.setMaximumWidth(340)
        splitter.addWidget(self._steps)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([260, 860, 280])

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

        fm = mb.addMenu("&Файл")
        fm.addAction("&Ново",         self._new_recipe,     "Ctrl+N")
        fm.addAction("&Отвори…",      self._open_recipe,    "Ctrl+O")
        fm.addAction("&Запази",       self._save_recipe,    "Ctrl+S")
        fm.addAction("Запази &като…", self._save_recipe_as, "Ctrl+Shift+S")
        fm.addSeparator()
        fm.addAction("&Експорт G-код…", self._export_gcode, "Ctrl+E")
        fm.addSeparator()
        fm.addAction("&Изход", QApplication.quit, "Ctrl+Q")

        tm = mb.addMenu("&Инструменти")
        tm.addAction("&Библиотека с ножове…", self._open_tool_editor, "Ctrl+T")
        if self._driver:
            tm.addAction("&Изпрати в LinuxCNC", self._send_to_linuxcnc, "Ctrl+L")

        vm = mb.addMenu("&Изглед")
        vm.addAction("&Вмести изглед", self._fit_canvas, "Ctrl+0")

        hm = mb.addMenu("&Помощ")
        hm.addAction("&За програмата", self._about)

    def _connect_signals(self) -> None:
        self._model.recipe_changed.connect(self._on_recipe_changed)
        self._model.selection_changed.connect(self._on_selection_changed)
        self._model.error_occurred.connect(self._show_error)

        self._sidebar.primitive_add.connect(self._on_primitive_chosen)
        self._sidebar.primitive_insert_before.connect(self._model.insert_operation_before)
        self._sidebar.primitive_insert_after.connect(self._model.insert_operation_after)

        self._toolbar.action_new.connect(self._new_recipe)
        self._toolbar.action_open.connect(self._open_recipe)
        self._toolbar.action_save.connect(self._save_recipe)
        self._toolbar.action_save_as.connect(self._save_recipe_as)
        self._toolbar.action_export.connect(self._export_gcode)
        self._toolbar.action_fit.connect(self._fit_canvas)
        self._toolbar.action_3d.connect(self._show_3d_view)

        self._canvas.segment_selected.connect(self._model.select)
        self._canvas.request_delete.connect(self._handle_canvas_delete)
        self._canvas.request_insert.connect(self._handle_canvas_insert)
        self._canvas.request_stock_edit.connect(self._open_stock_panel)
        self._model.selection_changed.connect(self._sync_canvas_selection)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_primitive_chosen(self, name: str) -> None:
        self._model.add_operation(name)

    def _on_recipe_changed(self) -> None:
        profile = self._model.profile
        self._canvas.set_profile(profile)
        mat = self._model.material_library.get(self._model.recipe.stock.material_key)
        self._canvas.set_material_category(mat.category if mat else "Steel")
        self._status_cursor.setText(
            f"X: {profile.cursor_x:.2f} mm   Z: {profile.cursor_z:.2f} mm"
        )
        seqs = self._model.recipe.tool_sequences
        sel  = max(self._model.selected_seq, 0)
        if seqs and sel < len(seqs):
            t = seqs[sel].tool_id
            self._status_tool.setText(f"T{t:02d}")
            self._canvas.set_active_tool(self._model.tool_library.get_by_id(t))
        if self._canvas3d and self._canvas3d.isVisible():
            self._canvas3d.update_3d_model(profile)

    def _on_selection_changed(self, si: int, oi: int) -> None:
        seqs, sel = self._model.recipe.tool_sequences, max(si, 0)
        if seqs and sel < len(seqs):
            self._canvas.set_active_tool(self._model.tool_library.get_by_id(seqs[sel].tool_id))

    def _show_error(self, msg: str) -> None:
        self._status_err.setText(msg)

    def _fit_canvas(self) -> None:
        self._canvas._fit_pending = True
        self._canvas.update()

    def _show_3d_view(self) -> None:
        if self._canvas3d is None:
            self._canvas3d = Canvas3D()
        self._canvas3d.update_3d_model(self._model.profile)
        self._canvas3d.show_window()

    # ------------------------------------------------------------------
    # File actions
    # ------------------------------------------------------------------

    def _new_recipe(self) -> None:
        self._model.new_recipe()
        self._recipe_path = None
        self.setWindowTitle("LatheCadCam — Нова деталь")

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

    def _build_writer(self) -> GCodeWriter:
        return GCodeWriter(
            recipe=self._model.recipe, profile=self._model.profile,
            tool_library=self._model.tool_library, machine=self._machine,
            app_config=self._app_config)

    def _export_gcode(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Експорт G-код", "", "G-код файлове (*.ngc *.nc *.gcode)")
        if not path:
            return
        try:
            Path(path).write_text(self._build_writer().generate(), encoding="utf-8")
            self.statusBar().showMessage(f"G-код записан: {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Грешка при генериране", str(e))

    def _send_to_linuxcnc(self) -> None:
        try:
            dest = self._driver.inject_gcode(self._build_writer().generate())
            self.statusBar().showMessage(f"LinuxCNC: зареден {dest.name}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "LinuxCNC грешка", str(e))

    def _sync_canvas_selection(self, seq_idx: int, op_idx: int) -> None:
        self._canvas.set_selected_tag(seq_idx, op_idx)

    def _handle_canvas_delete(self, seq_idx: int, op_idx: int) -> None:
        self._model.select(seq_idx, op_idx)
        self._model.remove_selected()

    def _handle_canvas_insert(
        self, seq_idx: int, op_idx: int, direction_str: str, primitive_name: str
    ) -> None:
        direction = (
            ToolDirection.EXTERNAL if direction_str == "external"
            else ToolDirection.INTERNAL
        )
        self._model.insert_at(seq_idx, op_idx, primitive_name, direction)

    def _open_stock_panel(self) -> None:
        from ui.stock_panel import StockEditDialog
        StockEditDialog(self._model, self).exec()

    def _open_tool_editor(self) -> None:
        dlg = ToolEditor(
            self._model.tool_library,
            self._model.material_library,
            save_path=self._tool_library_path,
            parent=self,
        )
        dlg.exec()
        # Refresh model with possibly-edited library
        updated = dlg.get_library()
        self._model.tool_library = updated

    def _about(self) -> None:
        QMessageBox.about(self, "За LatheCadCam",
            "<b>LatheCadCam</b><br>Конверсационен CAM редактор за стругове.<br>"
            "Работи самостоятелно или като добавка за LinuxCNC.")
