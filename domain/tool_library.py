"""
ToolLibrary — load, save, and query a collection of Tool objects.

Persists to a JSON file.  One library file per manufacturer catalogue
or per machine (e.g. data/tools/sandvik.json, data/tools/my_lathe.json).

Kept separate from tool.py to respect the 300-line file limit and to
isolate serialisation concerns from the domain model.
"""

from __future__ import annotations

import json
from pathlib import Path

from domain.tool import (
    CuttingData, InsertClearance, InsertShape, Tool,
    ToolDirection, ToolHand, ToolHolder, ToolInsert,
)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _insert_to_dict(ins: ToolInsert) -> dict:
    return {
        "shape":        ins.shape.value,
        "clearance":    ins.clearance.value,
        "nose_radius":  ins.nose_radius,
        "ic_size":      ins.ic_size,
        "thickness":    ins.thickness,
        "manufacturer": ins.manufacturer,
        "iso_code":     ins.iso_code,
    }


def _insert_from_dict(d: dict) -> ToolInsert:
    return ToolInsert(
        shape=InsertShape(d.get("shape", "C")),
        clearance=InsertClearance(d.get("clearance", "N")),
        nose_radius=d.get("nose_radius", 0.4),
        ic_size=d.get("ic_size", 12.7),
        thickness=d.get("thickness", 4.76),
        manufacturer=d.get("manufacturer", ""),
        iso_code=d.get("iso_code", ""),
    )


def _holder_to_dict(h: ToolHolder) -> dict:
    return {
        "approach_angle": h.approach_angle,
        "hand":           h.hand.value,
        "direction":      h.direction.value,
        "shank_w":        h.shank_w,
        "shank_h":        h.shank_h,
        "manufacturer":   h.manufacturer,
        "iso_code":       h.iso_code,
    }


def _holder_from_dict(d: dict) -> ToolHolder:
    return ToolHolder(
        approach_angle=d.get("approach_angle", 95.0),
        hand=ToolHand(d.get("hand", "R")),
        direction=ToolDirection(d.get("direction", "external")),
        shank_w=d.get("shank_w", 25.0),
        shank_h=d.get("shank_h", 25.0),
        manufacturer=d.get("manufacturer", ""),
        iso_code=d.get("iso_code", ""),
    )


def _cutting_data_to_dict(cd: CuttingData) -> dict:
    return {
        "vc_rec":  cd.vc_rec,
        "vc_max":  cd.vc_max,
        "fn_rec":  cd.fn_rec,
        "fn_max":  cd.fn_max,
        "ap_rec":  cd.ap_rec,
        "ap_max":  cd.ap_max,
    }


def _cutting_data_from_dict(key: str, d: dict) -> CuttingData:
    return CuttingData(
        material_key=key,
        vc_rec=d.get("vc_rec", 200.0),
        vc_max=d.get("vc_max", 280.0),
        fn_rec=d.get("fn_rec", 0.20),
        fn_max=d.get("fn_max", 0.40),
        ap_rec=d.get("ap_rec", 2.0),
        ap_max=d.get("ap_max", 4.0),
    )


def _tool_to_dict(t: Tool) -> dict:
    return {
        "tool_id":     t.tool_id,
        "description": t.description,
        "insert":      _insert_to_dict(t.insert),
        "holder":      _holder_to_dict(t.holder),
        "cutting_data": {
            k: _cutting_data_to_dict(v)
            for k, v in t.cutting_data.items()
        },
    }


def _tool_from_dict(d: dict) -> Tool:
    return Tool(
        tool_id=d["tool_id"],
        description=d.get("description", ""),
        insert=_insert_from_dict(d.get("insert", {})),
        holder=_holder_from_dict(d.get("holder", {})),
        cutting_data={
            k: _cutting_data_from_dict(k, v)
            for k, v in d.get("cutting_data", {}).items()
        },
    )


# ---------------------------------------------------------------------------
# ToolLibrary
# ---------------------------------------------------------------------------

class ToolLibrary:
    """
    In-memory collection of Tool objects with load/save to JSON.

    Typical usage:
        lib = ToolLibrary.load(Path("data/tools/my_lathe.json"))
        tool = lib.get_by_id(1)
        lib.add(new_tool)
        lib.save(Path("data/tools/my_lathe.json"))
    """

    def __init__(self) -> None:
        self._tools: dict[int, Tool] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, tool: Tool) -> None:
        """Add or replace a tool by tool_id."""
        self._tools[tool.tool_id] = tool

    def remove(self, tool_id: int) -> None:
        self._tools.pop(tool_id, None)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_by_id(self, tool_id: int) -> Tool | None:
        return self._tools.get(tool_id)

    def all(self) -> list[Tool]:
        return sorted(self._tools.values(), key=lambda t: t.tool_id)

    def by_direction(self, direction: ToolDirection) -> list[Tool]:
        return [t for t in self.all() if t.direction == direction]

    def ids(self) -> list[int]:
        return sorted(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"tools": [_tool_to_dict(t) for t in self.all()]}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> "ToolLibrary":
        lib = cls()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for td in data.get("tools", []):
            lib.add(_tool_from_dict(td))
        return lib

    @classmethod
    def empty(cls) -> "ToolLibrary":
        return cls()
