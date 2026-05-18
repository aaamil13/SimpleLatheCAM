"""
Parting (cut-off) G-code generator.

Three chip-break modes:
  0 — continuous plunge straight to x_target
  1 — peck: plunge peck_depth, retract retract_amount, repeat
  2 — full retract: plunge peck_depth, retract fully to safe_x, repeat
"""

from __future__ import annotations


def _fmt(v: float) -> str:
    return f"{v:.3f}"


def parting_lines(
    params: dict,
    current_r: float,
    feed_rate: float,
    safe_x_r: float,
) -> list[str]:
    """Return G-code lines for a parting operation."""
    lines: list[str] = []
    x_target = params.get("x_target", 0.0)
    mode     = round(params.get("chip_break_mode", 0.0))
    peck_d   = params.get("peck_depth", 2.0)
    retract  = params.get("retract_amount", 0.5)
    safe_x   = params.get("safe_x", safe_x_r * 2.0)
    target_r = x_target / 2.0

    if mode == 0:
        lines.append(f"G1 X{_fmt(x_target)} F{feed_rate:.0f}")

    elif mode == 1:
        r = current_r - peck_d
        while r > target_r:
            lines.append(f"G1 X{_fmt(r * 2.0)} F{feed_rate:.0f}")
            lines.append(f"G1 X{_fmt((r + retract) * 2.0)} F{feed_rate * 2:.0f}")
            r -= peck_d
        lines.append(f"G1 X{_fmt(x_target)} F{feed_rate:.0f}")

    else:
        r = current_r - peck_d
        while r > target_r:
            lines.append(f"G1 X{_fmt(r * 2.0)} F{feed_rate:.0f}")
            lines.append(f"G0 X{_fmt(safe_x)}")
            lines.append(f"G0 X{_fmt(r * 2.0)}")
            r -= peck_d
        lines.append(f"G1 X{_fmt(x_target)} F{feed_rate:.0f}")

    return lines
