"""
Material library — workpiece material definitions.

Material keys are used as foreign keys in CuttingData (tool.py) to link
recommended cutting parameters to a specific material.

MaterialLibrary loads from a JSON file and provides lookup by key or name.
A built-in fallback list is embedded so the software works without any
data files (useful on a fresh install or in tests).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------

@dataclass
class Material:
    """
    Workpiece material descriptor.

    key          : unique identifier used in CuttingData and recipe JSON
                   (e.g. "steel_45", "aluminium_6061")
    name         : human-readable display name
    category     : broad group for UI filtering
    density      : g/cm³ (optional, for mass estimation)
    hardness_HB  : Brinell hardness (0 = unknown)
    notes        : free text (alloy standard, typical applications, etc.)
    """
    key:         str
    name:        str
    category:    str    = "Steel"
    density:     float  = 7.85    # g/cm³
    hardness_HB: int    = 0
    notes:       str    = ""


# ---------------------------------------------------------------------------
# Built-in fallback materials (always available, no file required)
# ---------------------------------------------------------------------------

_BUILTIN: list[dict] = [
    {
        "key": "steel_45", "name": "Steel 45 (C45)",
        "category": "Steel", "density": 7.85, "hardness_HB": 207,
        "notes": "Medium-carbon steel, common for shafts and gears.",
    },
    {
        "key": "steel_st37", "name": "St37 / S235",
        "category": "Steel", "density": 7.85, "hardness_HB": 120,
        "notes": "Structural mild steel, easy to machine.",
    },
    {
        "key": "steel_304ss", "name": "Stainless 304",
        "category": "Stainless", "density": 7.93, "hardness_HB": 201,
        "notes": "Austenitic stainless — work-hardening, reduce feed.",
    },
    {
        "key": "aluminium_6061", "name": "Aluminium 6061-T6",
        "category": "Aluminium", "density": 2.70, "hardness_HB": 95,
        "notes": "General-purpose aluminium alloy, excellent machinability.",
    },
    {
        "key": "aluminium_2024", "name": "Aluminium 2024-T4",
        "category": "Aluminium", "density": 2.78, "hardness_HB": 120,
        "notes": "High-strength aerospace alloy.",
    },
    {
        "key": "brass", "name": "Brass CW614N",
        "category": "Brass/Copper", "density": 8.50, "hardness_HB": 100,
        "notes": "Free-cutting brass — high surface speed.",
    },
    {
        "key": "cast_iron_grey", "name": "Grey Cast Iron GG20",
        "category": "Cast Iron", "density": 7.20, "hardness_HB": 200,
        "notes": "Brittle — use lower feed, no coolant preferred.",
    },
    {
        "key": "titanium_gr5", "name": "Titanium Grade 5 (Ti-6Al-4V)",
        "category": "Titanium", "density": 4.43, "hardness_HB": 334,
        "notes": "Low thermal conductivity — use flood coolant, low Vc.",
    },
]


# ---------------------------------------------------------------------------
# MaterialLibrary
# ---------------------------------------------------------------------------

class MaterialLibrary:
    """
    In-memory collection of Material objects.

    Always loads the built-in list first; a JSON file can extend or
    override individual entries (matched by key).
    """

    def __init__(self) -> None:
        self._materials: dict[str, Material] = {}
        self._load_builtin()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_builtin(self) -> None:
        for d in _BUILTIN:
            m = Material(**d)
            self._materials[m.key] = m

    def load_file(self, path: Path | str) -> None:
        """
        Merge materials from a JSON file.
        Entries with existing keys are updated; new keys are added.
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for d in data.get("materials", []):
            m = Material(**d)
            self._materials[m.key] = m

    def save(self, path: Path | str) -> None:
        """Save all materials (including built-ins) to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "materials": [
                {
                    "key":         m.key,
                    "name":        m.name,
                    "category":    m.category,
                    "density":     m.density,
                    "hardness_HB": m.hardness_HB,
                    "notes":       m.notes,
                }
                for m in self.all()
            ]
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, key: str) -> Material | None:
        return self._materials.get(key)

    def all(self) -> list[Material]:
        return sorted(self._materials.values(), key=lambda m: (m.category, m.name))

    def by_category(self) -> dict[str, list[Material]]:
        groups: dict[str, list[Material]] = {}
        for m in self.all():
            groups.setdefault(m.category, []).append(m)
        return groups

    def keys(self) -> list[str]:
        return list(self._materials.keys())

    def __len__(self) -> int:
        return len(self._materials)
