"""
bridge/linuxcnc_driver.py — Isolation layer for LinuxCNC communication.

Wraps the 'linuxcnc' Python module (only present on a real LinuxCNC machine)
so that the rest of the application runs unchanged on Windows / Mac / plain Linux.

When HAS_LINUXCNC is False every method is a safe no-op and
get_machine_status() returns a plausible offline dict.

LinuxCNC Python binding quick-reference:
  linuxcnc.command()  — send commands  (.program_open, .mdi, .mode, .wait_complete)
  linuxcnc.stat()     — poll machine state (.task_state, .current_tool, .file, ...)
  linuxcnc.error_channel() — drain error/info messages
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Conditional import — safe on non-LinuxCNC hosts
# ---------------------------------------------------------------------------

try:
    import linuxcnc as _lc          # type: ignore[import]
    HAS_LINUXCNC   = True
    _MODE_MDI      = _lc.MODE_MDI
    _STATE_ESTOP   = _lc.STATE_ESTOP
    _INTERP_IDLE   = _lc.INTERP_IDLE
except ImportError:
    _lc            = None           # type: ignore[assignment]
    HAS_LINUXCNC   = False
    _MODE_MDI      = 2
    _STATE_ESTOP   = 1
    _INTERP_IDLE   = 1

# Default directory where LinuxCNC looks for G-code programs
NC_FILES_DIR: Path = Path.home() / "linuxcnc" / "nc_files"


# ---------------------------------------------------------------------------
# Driver class
# ---------------------------------------------------------------------------

class LinuxCNCDriver:
    """
    Thin isolation wrapper around the LinuxCNC Python bindings.

    Instantiate once at application start.  Pass it to any UI component
    that needs to communicate with the controller.  When HAS_LINUXCNC is
    False all operations silently degrade so the editor is still usable
    for offline programming.
    """

    def __init__(self) -> None:
        if HAS_LINUXCNC:
            self._cmd  = _lc.command()
            self._stat = _lc.stat()
            self._err  = _lc.error_channel()
        else:
            self._cmd = self._stat = self._err = None

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """True when the linuxcnc module is loaded and command channel is open."""
        return HAS_LINUXCNC and self._cmd is not None

    # ------------------------------------------------------------------
    # G-code injection
    # ------------------------------------------------------------------

    def inject_gcode(
        self,
        text: str,
        filename: str = "latheCadCam_output.ngc",
    ) -> Path:
        """
        Write *text* to nc_files dir and load it in the LinuxCNC interpreter.

        Returns the path the file was written to (useful for logging / UI).
        When not on a LinuxCNC host the file is still written so it can be
        copied to the machine manually.
        """
        dest = NC_FILES_DIR / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        if self._cmd is not None:
            self._cmd.program_open(str(dest))
        return dest

    # ------------------------------------------------------------------
    # Machine status
    # ------------------------------------------------------------------

    def get_machine_status(self) -> dict:
        """
        Return a neutral status dict safe to use regardless of platform.

        Keys
        ----
        estop        : bool — machine is in E-stop
        current_tool : int  — currently loaded tool number
        file_loaded  : str  — path of the currently loaded G-code file
        running      : bool — interpreter is executing a program
        """
        if self._stat is None:
            return {
                "estop": True, "current_tool": 0,
                "file_loaded": "", "running": False,
            }
        self._stat.poll()
        return {
            "estop":        self._stat.task_state == _STATE_ESTOP,
            "current_tool": self._stat.current_tool,
            "file_loaded":  self._stat.file or "",
            "running":      self._stat.interp_state != _INTERP_IDLE,
        }

    # ------------------------------------------------------------------
    # Tool offsets
    # ------------------------------------------------------------------

    def set_tool_offset(self, tool_id: int, x: float, z: float) -> None:
        """
        Set diameter (X) and Z offset for *tool_id* via G10 L1 MDI command.

        No-op when not connected to LinuxCNC.
        """
        if self._cmd is None:
            return
        self._cmd.mode(_MODE_MDI)
        self._cmd.wait_complete()
        self._cmd.mdi(f"G10 L1 P{tool_id} X{x:.4f} Z{z:.4f}")
        self._cmd.wait_complete()

    # ------------------------------------------------------------------
    # Error channel
    # ------------------------------------------------------------------

    def get_errors(self) -> list[str]:
        """
        Drain the LinuxCNC error channel and return all pending messages.

        Returns an empty list when not on a LinuxCNC host or when the
        channel has no pending messages.
        """
        if self._err is None:
            return []
        messages: list[str] = []
        while True:
            result = self._err.poll()
            if not result:
                break
            _kind, text = result
            messages.append(text)
        return messages
