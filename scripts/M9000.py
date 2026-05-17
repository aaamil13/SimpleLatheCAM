#!/usr/bin/env python3
"""
LinuxCNC user M-code: M9000 — operator confirmation dialog.

Installation
------------
Copy (or symlink) this file to your LinuxCNC USER_M_PATH directory and make
it executable:

    cp scripts/M9000.py ~/.linuxcnc/M9000
    chmod +x ~/.linuxcnc/M9000

In your machine INI file add:
    [RS274NGC]
    USER_M_PATH = ~/.linuxcnc

Usage in G-code
---------------
    M9000 P<message_index>

where <message_index> is the 0-based index into the messages JSON file.

Message file
------------
Written by LatheCadCam GCodeWriter to the path set by
$LATHECADCAM_MESSAGES (default /tmp/lathecadcam_messages.json).

Format:
    [
      {"index": 0, "title": "Потвърждение", "bg": "Text BG", "en": "Text EN"},
      ...
    ]

Language
--------
Set $LATHECADCAM_LANG to the ISO-639-1 language code (default: bg).

Exit codes
----------
    0  — operator confirmed → G-code continues
    1  — operator cancelled → LinuxCNC aborts the program
"""

import json
import os
import sys


_MESSAGES_FILE = os.environ.get(
    "LATHECADCAM_MESSAGES",
    "/tmp/lathecadcam_messages.json",
)
_LANG = os.environ.get("LATHECADCAM_LANG", "bg")


def _load_entry(idx: int) -> tuple[str, str]:
    try:
        with open(_MESSAGES_FILE, encoding="utf-8") as f:
            entries = json.load(f)
        entry = entries[idx]
        text = (
            entry.get(_LANG)
            or entry.get("en")
            or entry.get("bg")
            or "Потвърдете продължаването на програмата."
        )
        title = entry.get("title", "Оператор")
        return title, text
    except Exception:
        return "Оператор", "Потвърдете продължаването на програмата."


# ---------------------------------------------------------------------------
# Dialog back-ends (tried in order until one succeeds)
# ---------------------------------------------------------------------------

def _show_gtk(title: str, body: str) -> int:
    import gi                                       # type: ignore[import]
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk                  # type: ignore[import]
    dlg = Gtk.MessageDialog(
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
    )
    dlg.set_title(title)
    dlg.set_markup(f"<b>{title}</b>\n\n{body}")
    code = dlg.run()
    dlg.destroy()
    return 0 if code == Gtk.ResponseType.OK else 1


def _show_zenity(title: str, body: str) -> int:
    import subprocess
    r = subprocess.run(
        ["zenity", "--question",
         f"--title={title}",
         f"--text={body}",
         "--ok-label=Продължи",
         "--cancel-label=Стоп",
         "--width=400"],
        timeout=3600,
    )
    return r.returncode


def _show_tkinter(title: str, body: str) -> int:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    ok = messagebox.askokcancel(title, body)
    root.destroy()
    return 0 if ok else 1


def _show_terminal(title: str, body: str) -> int:
    line = "=" * 60
    print(f"\n{line}\n  {title}\n\n  {body}\n{line}", flush=True)
    try:
        answer = input("  Продължи? [y/N]: ").strip().lower()
        return 0 if answer in ("y", "yes", "д", "да") else 1
    except EOFError:
        return 0  # non-interactive mode → continue


# ---------------------------------------------------------------------------

def main() -> int:
    idx = int(float(sys.argv[1])) if len(sys.argv) > 1 else 0
    title, body = _load_entry(idx)

    for show_fn in (_show_gtk, _show_zenity, _show_tkinter, _show_terminal):
        try:
            return show_fn(title, body)
        except Exception:
            continue

    return 0   # all back-ends failed → continue program


if __name__ == "__main__":
    sys.exit(main())
