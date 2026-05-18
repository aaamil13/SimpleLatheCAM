"""canvas_tooltip — builds rich HTML tooltip text for a profile segment."""

from __future__ import annotations

from domain.profile_segments import ArcSegment, LineSegment


def build_tooltip(model, tag: tuple[int, int], seg: object) -> str | None:
    """Return an HTML string describing *seg* and its operation, or None."""
    seq_idx, op_idx = tag
    try:
        seq = model.recipe.tool_sequences[seq_idx]
        op  = seq.operations[op_idx]
    except IndexError:
        return None

    plugin    = model.loader.get(op.primitive_name)
    op_name   = plugin.display_name if plugin else op.primitive_name
    direction = "Вътрешна (Boring)" if op.direction.value == "internal" else "Външна (Turning)"

    mode = "CSS" if seq.spindle_mode.value == "G96" else "G97"
    unit = "m/min" if mode == "CSS" else "об/мин"
    spindle = f"<b>{seq.spindle_value:.0f} {unit}</b> [{mode}]"

    geom = _geom_line(seg)

    params = "".join(
        f"• {k}: <b>{v:.3g}</b><br>" for k, v in op.params.items()
    )

    hr = "<hr style='border:none;border-top:1px solid #37474F;margin:3px 0'>"
    return (
        f"<div style='white-space:nowrap'>"
        f"<h4 style='margin:0 0 4px 0;color:#4FC3F7'>{op_name}</h4>"
        f"<span style='color:#CFD8DC'>Посока: {direction}</span><br>{hr}"
        f"<span style='color:#81C784'><b>Контур:</b></span><br>{geom}<br>{hr}"
        f"<span style='color:#FFB74D'><b>Параметри:</b></span><br>{params}{hr}"
        f"Инструмент: <b>T{seq.tool_id:02d}</b> · {spindle}"
        f"</div>"
    )


def _geom_line(seg: object) -> str:
    if isinstance(seg, LineSegment):
        length = abs(seg.z1 - seg.z0)
        d0, d1 = seg.x0 * 2, seg.x1 * 2
        if length > 0.001:
            return f"Дължина (Z): <b>{length:.2f} mm</b><br>⌀{d0:.2f} ➔ ⌀{d1:.2f}"
        return f"Челен ход: ⌀{d0:.2f} ➔ ⌀{d1:.2f}"
    if isinstance(seg, ArcSegment):
        return (
            f"Радиус: <b>R{seg.radius:.2f}</b><br>"
            f"⌀{seg.x0 * 2:.2f} ➔ ⌀{seg.x1 * 2:.2f}"
        )
    return ""
