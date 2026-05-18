"""
Operator message and manual-spindle G-code helpers.

Handles operator dialogs (M0 or custom M-code pause) and collects
message catalogue entries written to disk for M9000.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.app_config import AppConfig
    from domain.recipe import OperationRecord


class MessageCatalogue:
    """Collects operator messages and writes the catalogue file for M9000."""

    def __init__(self, app_config: "AppConfig") -> None:
        self._cfg      = app_config
        self._messages: list[dict] = []

    def reset(self) -> None:
        self._messages = []

    def register(self, extras: dict, title: str) -> int:
        idx   = len(self._messages)
        entry = {"index": idx, "title": title}
        entry.update(extras)
        self._messages.append(entry)
        return idx

    def confirm_pause(self, idx: int) -> list[str]:
        cfg = self._cfg
        if cfg.use_confirm_mcode:
            return [
                f"M{cfg.confirm_mcode} P{idx}"
                f"  (operator dialog — needs M{cfg.confirm_mcode} in USER_M_PATH)",
            ]
        return ["M0         (pause — press CYCLE START to continue)"]

    def flush(self) -> None:
        if not self._messages:
            return
        path = Path(self._cfg.messages_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._messages, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    # ------------------------------------------------------------------

    def operator_message_lines(self, op: "OperationRecord") -> list[str]:
        text = self._cfg.message_text(op.extras)
        if not text:
            text = "Operator action required"
        lines: list[str] = [self._cfg.format_gcode_msg(text)]
        require = op.params.get("require_confirm", 1.0) > 0.5
        if require:
            idx = self.register(op.extras, "Потвърждение")
            lines.extend(self.confirm_pause(idx))
        return lines

    def manual_spindle_lines(
        self, op: "OperationRecord", machine_cap_rpm, seq_max_rpm: int
    ) -> list[str]:
        rpm = op.params.get("spindle_rpm", 500.0)
        rpm = machine_cap_rpm(rpm) if machine_cap_rpm else min(rpm, seq_max_rpm)
        text = self._cfg.message_text(op.extras)
        if not text:
            text = "Ръчна операция — натиснете CYCLE START след приключване"
        idx = self.register(op.extras or {"bg": text}, "Ръчна операция")
        lines: list[str] = [
            f"G97 S{rpm:.0f} M3  (manual spindle operation)",
            self._cfg.format_gcode_msg(text),
        ]
        lines.extend(self.confirm_pause(idx))
        lines.append("M5         (spindle off)")
        return lines
