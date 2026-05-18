"""
ActionToolbar — top QToolBar with file and view actions.

Buttons: New · Open · Save · Save As · | · Export G-code · | · Fit View

Signals
-------
  action_new
  action_open
  action_save
  action_save_as
  action_export
  action_fit
  action_3d
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QToolBar


class ActionToolbar(QToolBar):
    action_new     = Signal()
    action_open    = Signal()
    action_save    = Signal()
    action_save_as = Signal()
    action_export  = Signal()
    action_fit     = Signal()
    action_3d      = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Действия", parent)
        self.setMovable(False)

        self._add("Ново",          "Ctrl+N",          self.action_new)
        self._add("Отвори…",       "Ctrl+O",          self.action_open)
        self._add("Запази",        "Ctrl+S",          self.action_save)
        self._add("Запази като…",  "Ctrl+Shift+S",    self.action_save_as)
        self.addSeparator()
        self._add("Експорт G-код…","Ctrl+E",          self.action_export)
        self.addSeparator()
        self._add("Вмести изглед", "Ctrl+0",          self.action_fit)
        self.addSeparator()
        self._add("3D изглед",     "Ctrl+3",          self.action_3d)

        self.setStyleSheet("""
            QToolBar {
                background: #263238;
                border-bottom: 1px solid #37474F;
                spacing: 2px;
                padding: 2px 4px;
            }
            QToolButton {
                color: #CFD8DC;
                background: transparent;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QToolButton:hover {
                background: #37474F;
            }
            QToolButton:pressed {
                background: #455A64;
            }
        """)

    def _add(self, label: str, shortcut: str, signal: Signal) -> None:
        act = self.addAction(label)
        act.setShortcut(shortcut)
        act.triggered.connect(signal)
