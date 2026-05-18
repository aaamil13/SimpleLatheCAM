"""
Tests for cam/gcode_writer.py and cam/finishing.py — G-code output correctness.

G41/G42 controller compensation is NOT used in this project — the tool offset
is computed explicitly via cam.profile_offset so the output works on any
controller.  Tests here verify the explicit-offset behaviour.
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.profile import LatheProfile
from cam.finishing import FinishingPass
from cam.gcode_writer import GCodeWriter, WriterConfig


# ---------------------------------------------------------------------------
# FinishingPass — basic output checks
# ---------------------------------------------------------------------------

def _straight_profile() -> LatheProfile:
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_cylinder(d=30.0, length=50.0)
    return p


def test_finishing_pass_contains_g1():
    profile = _straight_profile()
    fin = FinishingPass(profile=profile, feed_rate=120.0)
    lines = fin.lines()
    assert any("G1" in l for l in lines)


def test_finishing_pass_approach_rapid():
    profile = _straight_profile()
    fin = FinishingPass(profile=profile, feed_rate=120.0)
    lines = fin.lines()
    assert any("G0" in l for l in lines[:3]), "Expected rapid approach at the start"


def test_finishing_pass_no_controller_compensation():
    """Project uses explicit offset — G41/G42 must never appear."""
    profile = _straight_profile()
    for internal in (False, True):
        fin = FinishingPass(profile=profile, feed_rate=100.0, internal=internal)
        lines = fin.lines()
        assert not any("G41" in l or "G42" in l for l in lines), (
            f"G41/G42 found in finishing lines (internal={internal})"
        )


def test_finishing_pass_nose_radius_shifts_x_outward():
    """External finishing with nose_radius > 0 must produce larger X values."""
    profile = _straight_profile()
    nose = 0.4

    fin_no_offset = FinishingPass(profile=profile, feed_rate=100.0, nose_radius=0.0)
    fin_offset    = FinishingPass(profile=profile, feed_rate=100.0, nose_radius=nose)

    def _x_values(lines):
        xs = []
        for l in lines:
            if l.startswith("G1") and "X" in l:
                for tok in l.split():
                    if tok.startswith("X"):
                        xs.append(float(tok[1:]))
        return xs

    xs_plain  = _x_values(fin_no_offset.lines())
    xs_offset = _x_values(fin_offset.lines())

    assert xs_plain and xs_offset, "No G1 X moves found"
    # Every offset X should be exactly nose*2 larger
    for xp, xo in zip(xs_plain, xs_offset):
        assert abs(xo - xp - nose * 2) < 1e-3, (
            f"Expected X offset of {nose*2:.3f}, got {xo - xp:.3f}"
        )


def test_finishing_pass_internal_shifts_x_inward():
    """Boring pass (internal=True) must produce smaller X values than the raw profile."""
    profile = _straight_profile()
    nose = 0.4

    fin_no_offset = FinishingPass(profile=profile, feed_rate=100.0, nose_radius=0.0)
    fin_internal  = FinishingPass(profile=profile, feed_rate=100.0,
                                  nose_radius=nose, internal=True)

    def _x_values(lines):
        return [
            float(tok[1:])
            for l in lines if l.startswith("G1") and "X" in l
            for tok in l.split() if tok.startswith("X")
        ]

    xs_plain    = _x_values(fin_no_offset.lines())
    xs_internal = _x_values(fin_internal.lines())

    assert xs_plain and xs_internal
    for xp, xi in zip(xs_plain, xs_internal):
        assert abs(xi - xp + nose * 2) < 1e-3, (
            f"Expected inward X offset of {nose*2:.3f}, got {xp - xi:.3f}"
        )


# ---------------------------------------------------------------------------
# GCodeWriter integration
# ---------------------------------------------------------------------------

def _make_recipe_and_profile():
    """Minimal recipe + matching profile for writer tests."""
    from domain.recipe import PartRecipe, StockSpec, ToolSequence, OperationRecord
    from domain.tool import SpindleMode, ToolDirection

    profile = LatheProfile(stock_d=50.0, stock_l=100.0)
    profile.add_cylinder(d=30.0, length=50.0)

    stock = StockSpec(diameter=50.0, length=100.0, material_key="steel_45")
    seq = ToolSequence(
        tool_id=1,
        spindle_mode=SpindleMode.CSS,
        spindle_value=180.0,
        max_rpm=2000,
        coolant_on=False,
        operations=[
            OperationRecord(
                primitive_name="cylinder",
                params={"d": 30.0, "length": 50.0},
                direction=ToolDirection.EXTERNAL,
            )
        ],
    )
    recipe = PartRecipe(
        part_name="test_part",
        stock=stock,
        tool_sequences=[seq],
    )
    return recipe, profile


def _empty_library():
    from domain.tool_library import ToolLibrary
    return ToolLibrary.empty()


def test_gcode_writer_produces_output():
    recipe, profile = _make_recipe_and_profile()
    writer = GCodeWriter(recipe, profile, _empty_library())
    code = writer.generate()
    assert len(code) > 0
    assert "M30" in code


def test_gcode_writer_header_present():
    recipe, profile = _make_recipe_and_profile()
    writer = GCodeWriter(recipe, profile, _empty_library())
    lines = writer.generate_lines()
    assert any("G21" in l for l in lines)
    assert any("G18" in l for l in lines)
    assert any("G90" in l for l in lines)


def test_gcode_writer_spindle_css():
    recipe, profile = _make_recipe_and_profile()
    writer = GCodeWriter(recipe, profile, _empty_library())
    lines = writer.generate_lines()
    assert any("G96" in l for l in lines)


def test_gcode_writer_tool_change():
    recipe, profile = _make_recipe_and_profile()
    writer = GCodeWriter(recipe, profile, _empty_library())
    lines = writer.generate_lines()
    assert any("M6" in l for l in lines)


def test_gcode_writer_footer():
    recipe, profile = _make_recipe_and_profile()
    writer = GCodeWriter(recipe, profile, _empty_library())
    lines = writer.generate_lines()
    assert lines[-1] == "M30"
    assert any("M5" in l for l in lines)
