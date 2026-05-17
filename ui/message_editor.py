"""
MessageEditor — multilingual text editor for OperatorMessage operations.

Shows one text area per supported language.  The primary language
(from AppConfig) is highlighted.  Emits extras_changed(dict) on every
keystroke so the model stays in sync without a Save button.

Usage inside OperationEditDialog:
    editor = MessageEditor(op.extras, primary_lang="bg")
    editor.extras_changed.connect(lambda d: op.__setattr__("extras", d))
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from domain.app_config import SUPPORTED_LANGUAGES

_LANG_STYLE_PRIMARY = (
    "QPlainTextEdit { border: 1px solid #4FC3F7; border-radius:3px;"
    " background:#1E272E; color:#ECEFF1; }"
)
_LANG_STYLE_NORMAL = (
    "QPlainTextEdit { border: 1px solid #37474F; border-radius:3px;"
    " background:#1E272E; color:#CFD8DC; }"
)


class MessageEditor(QWidget):
    """Emits extras_changed({lang_code: text, ...}) on every edit."""

    extras_changed = Signal(dict)

    def __init__(
        self,
        extras:       dict[str, str],
        primary_lang: str = "bg",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._primary = primary_lang
        self._editors: dict[str, QPlainTextEdit] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        header = QLabel("Текст на съобщението")
        header.setStyleSheet("color:#90A4AE; font-size:10px; font-weight:bold;")
        layout.addWidget(header)

        for code, display_name in SUPPORTED_LANGUAGES.items():
            lbl = QLabel(f"{display_name}:")
            lbl.setStyleSheet(
                "color:#4FC3F7; font-size:10px;" if code == primary_lang
                else "color:#78909C; font-size:10px;"
            )
            layout.addWidget(lbl)

            ed = QPlainTextEdit()
            ed.setPlaceholderText(f"Въведете съобщение на {display_name}…")
            ed.setFixedHeight(60)
            ed.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            ed.setStyleSheet(
                _LANG_STYLE_PRIMARY if code == primary_lang else _LANG_STYLE_NORMAL
            )
            ed.setPlainText(extras.get(code, ""))
            ed.textChanged.connect(self._emit)
            self._editors[code] = ed
            layout.addWidget(ed)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#37474F;")
        layout.addWidget(sep)

    # ------------------------------------------------------------------

    def current_extras(self) -> dict[str, str]:
        return {
            code: ed.toPlainText().strip()
            for code, ed in self._editors.items()
        }

    def set_primary_language(self, lang: str) -> None:
        """Highlight the new primary language editor."""
        self._primary = lang
        for code, ed in self._editors.items():
            ed.setStyleSheet(
                _LANG_STYLE_PRIMARY if code == lang else _LANG_STYLE_NORMAL
            )

    def _emit(self) -> None:
        self.extras_changed.emit(self.current_extras())
