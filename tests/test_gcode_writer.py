"""
Tests for cam/gcode_writer.py and cam/finishing.py — G-code output correctness.
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.profile import LatheProfile
from domain.profile_segments import LineSegment, ArcSegment, ArcDirection
from cam.finishing import FinishingPass, _line_to_gcode, _arc_to_gcode
from cam.gcode_writer import GCodeWriter, WriterConfig


# ---------------------------------------------------------------------------
# Finishing helpers
# ---------------------------------------------------------------------------

def test_line_segment_gcode():
    seg = LineSegment(x0=12.5, z0=0.0, x1=12.5, z1=-30.0)
    code = _line_to_gcode(seg, feed=120.0)
    assert "G1" in code
    assert "X25.000" in code
    assert "Z-30.000" in code
    assert "F120" in code


def test_arc_segment_gcode_cw():
    seg = ArcSegment(
        x0=10.0, z0=0.0, x1=12.0, z1=-2.0,
        cx=10.0, cz=-2.0, radius=2.0,
        direction=ArcDirection.CW,
    )
    code = _arc_to_gcode(seg, feed=100.0)
    assert code.startswith("G2")
    assert "X24.000" in code
    assert "I0.000" in code   # cx - x0 = 0


def test_arc_segment_gcode_ccw():
    seg = ArcSegment(
        x0=10.0, z0=0.0, x1=12.0, z1=-2.0,
        cx=10.0, cz=-2.0, radius=2.0,
        direction=ArcDirection.CCW,
    )
    code = _arc_to_gcode(seg, feed=100.0)
    assert code.startswith("G3")


# ---------------------------------------------------------------------------
# FinishingPass
# ---------------------------------------------------------------------------

def _straight_profile() -> LatheProfile:
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_cylinder(d=30.0, length=50.0)
    return p


def test_finishing_pass_contains_g1():
    profile = _straight_profile()
    fin = FinishingPass(profile=profile, feed_rate=120.0, tool_id=0)
    lines = fin.lines()
    assert any("G1" in l for l in lines)


def test_finishing_pass_approach_rapid():
    profile = _straight_profile()
    fin = FinishingPass(profile=profile, feed_rate=120.0)
    lines = fin.lines()
    assert any("G0" in l for l in lines[:3]), "Expected rapid approach at the start"


def test_finishing_pass_compensation_external():
    profile = _straight_profile()
    fin = FinishingPass(profile=profile, feed_rate=100.0, tool_id=3, internal=False)
    lines = fin.lines()
    assert any("G42" in l for l in lines)
    assert any("G40" in l for l in lines)


def test_finishing_pass_compensation_internal():
    profile = _straight_profile()
    fin = FinishingPass(profile=profile, feed_rate=100.0, tool_id=3, internal=True)
    lines = fin.lines()
    assert any("G41" in l for l in lines)


def test_finishing_pass_no_compensation_when_tool_id_zero():
    profile = _straight_profile()
    fin = FinishingPass(profile=profile, feed_rate=100.0, tool_id=0)
    lines = fin.lines()
    assert not any("G41" in l or "G42" in l for l in lines)


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
