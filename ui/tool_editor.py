"""
ToolEditor — modal dialog for managing the ToolLibrary.

Layout
------
  [QListWidget — tool list]    [Add] [Edit] [Remove]
  [Save path label]            [Save] [Close]

Opens ToolEditDialog for Add and Edit.
The caller must check accepted() and retrieve the updated library via
get_library() if they want to persist changes to disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from domain.material import MaterialLibrary
from domain.tool import Tool, ToolInsert, ToolHolder
from domain.tool_library import ToolLibrary
from ui.tool_edit_dialog import ToolEditDialog


class ToolEditor(QDialog):
    """
    Browse, add, edit, and remove tools in a ToolLibrary.

    Usage::
        dlg = ToolEditor(lib, material_library, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            lib = dlg.get_library()
            lib.save(path)
    """

    def __init__(
        self,
        library:          ToolLibrary,
        material_library: MaterialLibrary,
        save_path:        Optional[Path] = None,
        parent:           Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Библиотека с инструменти")
        self.setMinimumSize(480, 400)

        self._library          = ToolLibrary()
        self._material_library = material_library
        self._save_path        = save_path

        # Deep-copy all tools into our local library
        for t in library.all():
            self._library.add(t)

        self._build_ui()
        self._refresh_list()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # List + side buttons
        row = QHBoxLayout()
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemDoubleClicked.connect(self._edit_tool)
        row.addWidget(self._list, 1)

        btns = QVBoxLayout()
        self._btn_add    = QPushButton("Добави")
        self._btn_edit   = QPushButton("Редактирай")
        self._btn_remove = QPushButton("Премахни")
        self._btn_add.clicked.connect(self._add_tool)
        self._btn_edit.clicked.connect(self._edit_tool)
        self._btn_remove.clicked.connect(self._remove_tool)
        for b in (self._btn_add, self._btn_edit, self._btn_remove):
            btns.addWidget(b)
        btns.addStretch()
        row.addLayout(btns)
        root.addLayout(row)

        # Save path row
        path_row = QHBoxLayout()
        self._path_lbl = QLabel(str(self._save_path or "—"))
        self._path_lbl.setWordWrap(True)
        path_row.addWidget(QLabel("Файл:"), 0)
        path_row.addWidget(self._path_lbl, 1)
        btn_browse = QPushButton("…")
        btn_browse.setFixedWidth(28)
        btn_browse.clicked.connect(self._browse_path)
        path_row.addWidget(btn_browse)
        root.addLayout(path_row)

        # Bottom buttons
        bottom = QHBoxLayout()
        btn_save = QPushButton("Запази")
        btn_save.clicked.connect(self._save)
        bottom.addWidget(btn_save)
        bottom.addStretch()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.accept)
        bottom.addWidget(bb)
        root.addLayout(bottom)

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        self._list.clear()
        for tool in self._library.all():
            dir_tag = "Ext" if tool.holder.direction.value == "external" else "Int"
            text = (
                f"T{tool.tool_id:02d}  [{dir_tag}]  "
                f"{tool.insert.shape.value}{tool.insert.clearance.value}"
                f"  Rε={tool.insert.nose_radius:.2f}"
            )
            if tool.description:
                text += f"  —  {tool.description}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, tool.tool_id)
            self._list.addItem(item)

    def _selected_id(self) -> Optional[int]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _add_tool(self) -> None:
        existing_ids = set(self._library.ids())
        new_id = next(i for i in range(1, 100) if i not in existing_ids)
        blank = Tool(
            tool_id=new_id,
            insert=ToolInsert(),
            holder=ToolHolder(),
        )
        dlg = ToolEditDialog(blank, self._material_library, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tool = dlg.get_tool()
            if tool.tool_id in existing_ids:
                QMessageBox.warning(
                    self, "ID конфликт",
                    f"Инструмент T{tool.tool_id:02d} вече съществува."
                    " Изберете друг номер.",
                )
                return
            self._library.add(tool)
            self._refresh_list()

    def _edit_tool(self) -> None:
        tid = self._selected_id()
        if tid is None:
            return
        tool = self._library.get_by_id(tid)
        if tool is None:
            return
        dlg = ToolEditDialog(tool, self._material_library, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            edited = dlg.get_tool()
            if edited.tool_id != tid:
                # ID changed — remove old, add new
                self._library.remove(tid)
            self._library.add(edited)
            self._refresh_list()

    def _remove_tool(self) -> None:
        tid = self._selected_id()
        if tid is None:
            return
        reply = QMessageBox.question(
            self, "Изтриване",
            f"Изтриване на T{tid:02d}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._library.remove(tid)
            self._refresh_list()

    def _browse_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Запази библиотека", "", "JSON файлове (*.json)"
        )
        if path:
            self._save_path = Path(path)
            self._path_lbl.setText(str(self._save_path))

    def _save(self) -> None:
        if not self._save_path:
            self._browse_path()
            if not self._save_path:
                return
        try:
            self._library.save(self._save_path)
            QMessageBox.information(
                self, "Запазено",
                f"Библиотеката е записана:\n{self._save_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Грешка при запис", str(e))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_library(self) -> ToolLibrary:
        """Return the (possibly modified) library."""
        return self._library
