"""
Tests for Tool model, CuttingData, and ToolLibrary round-trip.
"""

import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.tool import (
    CuttingData, InsertClearance, InsertShape, SpindleMode, Tool,
    ToolDirection, ToolHand, ToolHolder, ToolInsert,
)
from domain.tool_library import ToolLibrary


# ---------------------------------------------------------------------------
# InsertShape angles
# ---------------------------------------------------------------------------

def test_insert_shape_angles():
    assert InsertShape.C.included_angle == 80.0
    assert InsertShape.V.included_angle == 35.0
    assert InsertShape.T.included_angle == 60.0


# ---------------------------------------------------------------------------
# CuttingData RPM calculation
# ---------------------------------------------------------------------------

def test_rpm_for_diameter():
    cd = CuttingData(material_key="steel_45", vc_rec=220.0)
    rpm = cd.rpm_for_diameter(50.0)
    expected = (220.0 * 1000.0) / (math.pi * 50.0)
    assert abs(rpm - expected) < 0.1


def test_rpm_zero_diameter():
    cd = CuttingData(material_key="steel_45", vc_rec=220.0)
    assert cd.rpm_for_diameter(0.0) == 0.0


# ---------------------------------------------------------------------------
# Tool shortcuts
# ---------------------------------------------------------------------------

def test_tool_nose_radius_shortcut():
    t = Tool(tool_id=1, insert=ToolInsert(nose_radius=0.8))
    assert t.nose_radius == 0.8


def test_tool_direction_shortcut():
    t = Tool(tool_id=1, holder=ToolHolder(direction=ToolDirection.INTERNAL))
    assert t.direction == ToolDirection.INTERNAL


def test_tool_best_data_fallback():
    t = Tool(tool_id=1)
    # No cutting data defined — should return generic fallback, not raise
    cd = t.best_data("steel_45")
    assert cd.material_key == "steel_45"
    assert cd.vc_rec > 0


def test_tool_best_data_first_when_key_missing():
    t = Tool(tool_id=1, cutting_data={
        "aluminium_6061": CuttingData("aluminium_6061", vc_rec=600.0),
    })
    cd = t.best_data("unknown_material")
    assert cd.vc_rec == 600.0


# ---------------------------------------------------------------------------
# ToolLibrary
# ---------------------------------------------------------------------------

def test_library_add_and_get():
    lib = ToolLibrary.empty()
    t = Tool(tool_id=2, description="test tool")
    lib.add(t)
    assert lib.get_by_id(2) is t
    assert len(lib) == 1


def test_library_remove():
    lib = ToolLibrary.empty()
    lib.add(Tool(tool_id=1))
    lib.remove(1)
    assert lib.get_by_id(1) is None
    assert len(lib) == 0


def test_library_by_direction():
    lib = ToolLibrary.empty()
    lib.add(Tool(tool_id=1, holder=ToolHolder(direction=ToolDirection.EXTERNAL)))
    lib.add(Tool(tool_id=2, holder=ToolHolder(direction=ToolDirection.INTERNAL)))
    ext = lib.by_direction(ToolDirection.EXTERNAL)
    assert len(ext) == 1 and ext[0].tool_id == 1


def test_library_all_sorted():
    lib = ToolLibrary.empty()
    lib.add(Tool(tool_id=5))
    lib.add(Tool(tool_id=1))
    lib.add(Tool(tool_id=3))
    ids = [t.tool_id for t in lib.all()]
    assert ids == [1, 3, 5]


def test_library_save_load_round_trip():
    lib = ToolLibrary.empty()
    t = Tool(
        tool_id=7,
        description="round-trip test",
        insert=ToolInsert(shape=InsertShape.V, nose_radius=0.4),
        holder=ToolHolder(hand=ToolHand.L, direction=ToolDirection.EXTERNAL),
        cutting_data={
            "steel_45": CuttingData("steel_45", vc_rec=250.0, fn_rec=0.15),
        },
    )
    lib.add(t)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    try:
        lib.save(path)
        loaded = ToolLibrary.load(path)

        assert len(loaded) == 1
        lt = loaded.get_by_id(7)
        assert lt is not None
        assert lt.description == "round-trip test"
        assert lt.insert.shape == InsertShape.V
        assert abs(lt.insert.nose_radius - 0.4) < 1e-9
        assert lt.holder.hand == ToolHand.L
        cd = lt.cutting_data.get("steel_45")
        assert cd is not None
        assert abs(cd.vc_rec - 250.0) < 1e-9
        assert abs(cd.fn_rec - 0.15) < 1e-9
    finally:
        path.unlink(missing_ok=True)


def test_example_library_loads():
    path = ROOT / "data" / "tools" / "example_library.json"
    assert path.exists(), f"Example library not found: {path}"
    lib = ToolLibrary.load(path)
    assert len(lib) == 3
    t1 = lib.get_by_id(1)
    assert t1 is not None
    assert t1.insert.nose_radius == 0.8
    assert "steel_45" in t1.cutting_data


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_insert_shape_angles,
        test_rpm_for_diameter,
        test_rpm_zero_diameter,
        test_tool_nose_radius_shortcut,
        test_tool_direction_shortcut,
        test_tool_best_data_fallback,
        test_tool_best_data_first_when_key_missing,
        test_library_add_and_get,
        test_library_remove,
        test_library_by_direction,
        test_library_all_sorted,
        test_library_save_load_round_trip,
        test_example_library_loads,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print()
    print("All tests passed." if not failed else f"{failed} test(s) failed.")
    sys.exit(failed)
