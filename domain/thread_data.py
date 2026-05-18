"""thread_data.py — standard thread tables for the threading primitive.

Covers: Metric Coarse (ISO 68-1), Metric Fine, UNC, UNF, NPT tapered pipe.
All dimensions in mm.  Depth uses the standard 60° formula: 0.6495 × pitch.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ThreadSpec:
    label:      str    # display name, e.g. "M6  p=1.00"
    pitch_mm:   float  # thread pitch (mm)
    depth_mm:   float  # full thread depth (mm) — used as G76 K
    taper_rate: float  # radius change per mm of Z (0 = cylindrical)
    family:     str    # "metric_coarse" | "metric_fine" | "unc" | "unf" | "npt"


def _d60(pitch: float) -> float:
    """Standard 60° thread depth: 0.6495 × pitch."""
    return round(0.6495 * pitch, 4)


def _d55(pitch: float) -> float:
    """Whitworth 55° thread depth: 0.6403 × pitch (BSP/BSPT)."""
    return round(0.6403 * pitch, 4)


# ---------------------------------------------------------------------------
# Metric Coarse — ISO 68-1
# ---------------------------------------------------------------------------
_MC = [
    ("M2",   0.40), ("M2.5", 0.45), ("M3",  0.50), ("M4",  0.70),
    ("M5",   0.80), ("M6",   1.00), ("M8",  1.25), ("M10", 1.50),
    ("M12",  1.75), ("M16",  2.00), ("M20", 2.50), ("M24", 3.00),
    ("M30",  3.50), ("M36",  4.00),
]

# Metric Fine — ISO 68-1 (selected sizes)
_MF = [
    ("M8×1.0",   1.00), ("M10×1.0",  1.00), ("M10×1.25", 1.25),
    ("M12×1.0",  1.00), ("M12×1.25", 1.25), ("M12×1.5",  1.50),
    ("M16×1.0",  1.00), ("M16×1.5",  1.50), ("M20×1.0",  1.00),
    ("M20×1.5",  1.50), ("M24×1.5",  1.50), ("M24×2.0",  2.00),
]

# UNC — ANSI B1.1 (tpi → mm pitch)
_UNC = [
    ("#6-32",  32), ("#8-32",  32), ("#10-24", 24),
    ("1/4-20", 20), ("5/16-18",18), ("3/8-16", 16),
    ("1/2-13", 13), ("5/8-11", 11), ("3/4-10", 10), ('1"-8',  8),
]

# UNF — ANSI B1.1
_UNF = [
    ("#6-40",  40), ("#8-36",  36), ("#10-32", 32),
    ("1/4-28", 28), ("5/16-24",24), ("3/8-24", 24),
    ("1/2-20", 20), ("5/8-18", 18), ("3/4-16", 16), ('1"-12', 12),
]

# NPT — American tapered pipe thread (ANSI B1.20.1)
# taper_rate: radius change per mm of Z = (3/4 in/ft) / (2 * 25.4) = 0.015625 / 2
_NPT_RATE = 0.0156250   # mm/mm (radius per axial mm) = 1:16 taper on radius
_NPT = [
    ('1/8" NPT',  27),
    ('1/4" NPT',  18),
    ('3/8" NPT',  18),
    ('1/2" NPT',  14),
    ('3/4" NPT',  14),
    ('1" NPT',    11.5),
]


# ---------------------------------------------------------------------------
# Combined flat list — indices used by threading.py std_idx param
# ---------------------------------------------------------------------------

def _build() -> list[ThreadSpec]:
    out: list[ThreadSpec] = []
    for name, p in _MC:
        out.append(ThreadSpec(f"{name}  p={p:.2f} (груба)", p, _d60(p), 0.0, "metric_coarse"))
    for name, p in _MF:
        out.append(ThreadSpec(f"{name}  (фина)",             p, _d60(p), 0.0, "metric_fine"))
    for name, tpi in _UNC:
        p = round(25.4 / tpi, 4)
        out.append(ThreadSpec(f"{name} UNC  p={p:.3f}",      p, _d60(p), 0.0, "unc"))
    for name, tpi in _UNF:
        p = round(25.4 / tpi, 4)
        out.append(ThreadSpec(f"{name} UNF  p={p:.3f}",      p, _d60(p), 0.0, "unf"))
    for name, tpi in _NPT:
        p = round(25.4 / tpi, 4)
        out.append(ThreadSpec(f"{name}  p={p:.3f} (конусна)", p, _d60(p), _NPT_RATE, "npt"))
    return out


THREADS: list[ThreadSpec] = _build()
THREAD_CHOICES: list[str] = [t.label for t in THREADS]


def get_thread(idx: int) -> ThreadSpec:
    """Return ThreadSpec at *idx*, clamped to valid range."""
    return THREADS[max(0, min(int(idx), len(THREADS) - 1))]


def get_effective_thread(params: dict) -> tuple[float, float, float]:
    """Return (pitch_mm, depth_mm, taper_rate) from a threading op params dict.

    std_idx == 0  → manual (reads 'pitch' and 'depth' keys from params).
    std_idx >= 1  → standard table (offset by 1 because index 0 = "Manual" in UI).
    """
    idx = int(round(params.get("std_idx", 0)))
    if idx > 0:
        spec = get_thread(idx - 1)
        return spec.pitch_mm, spec.depth_mm, spec.taper_rate
    pitch = params.get("pitch", 1.5)
    depth = params.get("depth", 0.0) or round(0.6495 * pitch, 4)
    return pitch, depth, 0.0


# Infeed mode → G76 Q angle
INFEED_CHOICES = [
    "Радиален (0°) — за чугун / специфични",
    "Водещ фланг (29.5°) — за стомана [препоръчан]",
    "Следящ фланг (−29.5°) — за алуминий / мек материал",
]

def get_infeed_angle(mode_idx: int) -> float:
    """Map infeed mode index to G76 Q angle."""
    return {0: 0.0, 1: 29.5, 2: -29.5}.get(int(mode_idx), 29.5)
