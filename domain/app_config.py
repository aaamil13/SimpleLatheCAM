"""
AppConfig — application-level settings (operator language, G-code style).

Loaded from data/app_config.json at startup.
Determines which language is used for operator messages in G-code output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


# Supported operator languages: code → display name
SUPPORTED_LANGUAGES: dict[str, str] = {
    "bg": "Български",
    "en": "English",
    "de": "Deutsch",
}


@dataclass
class AppConfig:
    """
    operator_language   : ISO-639-1 code used when selecting message text for
                          G-code (MSG,...) comments.
    gcode_msg_style     : "MSG" → (MSG, text) in LinuxCNC status bar;
                          "DEBUG" → terminal log
    use_confirm_mcode   : when True, confirmations emit M<confirm_mcode> P<idx>
                          (user M-code dialog) instead of plain M0.
                          Requires scripts/M9000.py installed as a user M-code.
    confirm_mcode       : which M-code number to call (default 9000 → M9000).
    messages_file       : path where the message catalogue JSON is written;
                          M9000 reads this file to get the dialog text.
    """
    operator_language:  str  = "bg"
    gcode_msg_style:    str  = "MSG"
    use_confirm_mcode:  bool = True
    confirm_mcode:      int  = 9000
    messages_file:      str  = "/tmp/lathecadcam_messages.json"

    # ------------------------------------------------------------------

    def message_text(self, extras: dict[str, str]) -> str:
        """
        Select the best available message text from an extras dict.
        Preference: configured language → "en" fallback → first available.
        """
        if not extras:
            return ""
        for lang in (self.operator_language, "en", "bg"):
            if lang in extras and extras[lang].strip():
                return extras[lang].strip()
        return next(iter(extras.values()), "")

    def format_gcode_msg(self, text: str) -> str:
        """Wrap text in the configured G-code message format."""
        tag = self.gcode_msg_style.upper()
        return f"({tag}, {text})"

    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path | str) -> "AppConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            operator_language=data.get("operator_language", "bg"),
            gcode_msg_style=data.get("gcode_msg_style", "MSG"),
            use_confirm_mcode=data.get("use_confirm_mcode", True),
            confirm_mcode=data.get("confirm_mcode", 9000),
            messages_file=data.get("messages_file", "/tmp/lathecadcam_messages.json"),
        )

    @classmethod
    def default(cls) -> "AppConfig":
        return cls()

    def _to_dict(self) -> dict:
        return {
            "operator_language":  self.operator_language,
            "gcode_msg_style":    self.gcode_msg_style,
            "use_confirm_mcode":  self.use_confirm_mcode,
            "confirm_mcode":      self.confirm_mcode,
            "messages_file":      self.messages_file,
        }
