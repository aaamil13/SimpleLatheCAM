"""
MachineToolConfig — tool inventory and turret configuration.

Installed tools  — tools physically mounted right now (turret positions
                   for ATC, or the single tool post for manual machines).
Available tools  — the shop inventory: tool IDs from ToolLibrary that
                   *can* be mounted on this machine.

Roles in the system
-------------------
  Recipe editor  : shows only available tools in the tool-selection UI;
                   warns when a required tool is not available.
  GCodeWriter    : validates that every tool_id in the recipe is installed
                   (for ATC) or at least available (for manual).
  ToolOptimizer  : uses available tools to suggest the optimal assignment
                   that minimises tool changes.
  LinuxCNC bridge: syncs installed positions with tool.tbl T-numbers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# InstalledTool — one turret slot or the active manual tool post
# ---------------------------------------------------------------------------

@dataclass
class InstalledTool:
    """
    A tool mounted in a specific position on the machine.

    For ATC machines:   position is the turret slot number (1-based).
    For manual lathes:  position is always 1 (single tool post).
    offset_x / offset_z are tool-length compensation values read from the
    machine (mm).  They are stored here for reference but are managed by
    LinuxCNC's own tool table.
    """
    position: int        # turret slot (1-based); 1 for manual machines
    tool_id:  int        # matches a Tool.tool_id in ToolLibrary
    offset_x: float = 0.0   # tool-length offset X (mm) — from tool.tbl
    offset_z: float = 0.0   # tool-length offset Z (mm) — from tool.tbl
    note:     str   = ""    # free-text (e.g. "roughing left, pre-set 15-03")


# ---------------------------------------------------------------------------
# MachineToolConfig
# ---------------------------------------------------------------------------

@dataclass
class MachineToolConfig:
    """
    Tool inventory and turret layout for one machine.

    Attributes
    ----------
    has_atc         : True if the machine has an automatic tool changer.
    turret_positions: Number of turret slots (ignored for manual machines).
    installed       : Mapping  position → InstalledTool (currently mounted).
    available_ids   : Set of tool_ids from ToolLibrary that may be used on
                      this machine.  Must be a superset of installed IDs.
    """
    has_atc:          bool = False
    turret_positions: int  = 1
    installed:        dict[int, InstalledTool] = field(default_factory=dict)
    available_ids:    set[int]                 = field(default_factory=set)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def install(self, tool: InstalledTool) -> None:
        """Mount a tool into a turret position.  Adds its id to available_ids."""
        if self.has_atc and tool.position > self.turret_positions:
            raise ValueError(
                f"Position {tool.position} exceeds turret capacity "
                f"({self.turret_positions})."
            )
        self.installed[tool.position] = tool
        self.available_ids.add(tool.tool_id)

    def uninstall(self, position: int) -> InstalledTool | None:
        """Remove the tool from *position*.  Does NOT remove from available_ids."""
        return self.installed.pop(position, None)

    def add_available(self, tool_id: int) -> None:
        """Mark a tool as available (in the shop inventory) without mounting it."""
        self.available_ids.add(tool_id)

    def remove_available(self, tool_id: int) -> None:
        """Remove from available inventory (also uninstalls from all positions)."""
        self.available_ids.discard(tool_id)
        to_remove = [p for p, t in self.installed.items() if t.tool_id == tool_id]
        for p in to_remove:
            del self.installed[p]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_installed(self, tool_id: int) -> bool:
        return any(t.tool_id == tool_id for t in self.installed.values())

    def is_available(self, tool_id: int) -> bool:
        return tool_id in self.available_ids

    def position_of(self, tool_id: int) -> int | None:
        """Return the turret position of *tool_id*, or None if not installed."""
        for pos, t in self.installed.items():
            if t.tool_id == tool_id:
                return pos
        return None

    def installed_ids(self) -> list[int]:
        return sorted(t.tool_id for t in self.installed.values())

    def missing_from_available(self, required_ids: list[int]) -> list[int]:
        """Return IDs in *required_ids* that are not in available_ids."""
        return [tid for tid in required_ids if tid not in self.available_ids]

    def missing_from_installed(self, required_ids: list[int]) -> list[int]:
        """Return IDs in *required_ids* that are not currently installed."""
        return [tid for tid in required_ids if not self.is_installed(tid)]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "has_atc":          self.has_atc,
            "turret_positions": self.turret_positions,
            "available_ids":    sorted(self.available_ids),
            "installed": [
                {
                    "position": t.position,
                    "tool_id":  t.tool_id,
                    "offset_x": t.offset_x,
                    "offset_z": t.offset_z,
                    "note":     t.note,
                }
                for t in sorted(self.installed.values(), key=lambda x: x.position)
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> "MachineToolConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cfg = cls(
            has_atc=data.get("has_atc", False),
            turret_positions=data.get("turret_positions", 1),
            available_ids=set(data.get("available_ids", [])),
        )
        for td in data.get("installed", []):
            cfg.installed[td["position"]] = InstalledTool(
                position=td["position"],
                tool_id=td["tool_id"],
                offset_x=td.get("offset_x", 0.0),
                offset_z=td.get("offset_z", 0.0),
                note=td.get("note", ""),
            )
        return cfg

    @classmethod
    def default(cls) -> "MachineToolConfig":
        """Single-tool-post manual lathe, no pre-configured tools."""
        return cls(has_atc=False, turret_positions=1)
