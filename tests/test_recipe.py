"""
Tests for Material library and PartRecipe serialisation.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.material import Material, MaterialLibrary
from domain.recipe import OperationRecord, PartRecipe, StockSpec, ToolSequence
from domain.tool import SpindleMode, ToolDirection


# ---------------------------------------------------------------------------
# MaterialLibrary
# ---------------------------------------------------------------------------

def test_builtin_materials_loaded():
    lib = MaterialLibrary()
    assert len(lib) >= 6
    assert lib.get("steel_45") is not None
    assert lib.get("aluminium_6061") is not None


def test_material_by_category():
    lib = MaterialLibrary()
    groups = lib.by_category()
    assert "Steel" in groups
    assert "Aluminium" in groups
    steel = groups["Steel"]
    assert all(m.category == "Steel" for m in steel)


def test_material_file_override():
    lib = MaterialLibrary()
    path = ROOT / "data" / "materials" / "default.json"
    assert path.exists(), "default.json not generated yet"
    lib.load_file(path)
    assert lib.get("steel_45") is not None   # still present after reload


def test_material_save_load_round_trip():
    lib = MaterialLibrary()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    try:
        lib.save(path)
        lib2 = MaterialLibrary()
        lib2.load_file(path)
        assert len(lib2) == len(lib)
    finally:
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# OperationRecord
# ---------------------------------------------------------------------------

def test_operation_record_defaults():
    op = OperationRecord("cylinder")
    assert op.direction == ToolDirection.EXTERNAL
    assert op.enabled is True
    assert op.params == {}


# ---------------------------------------------------------------------------
# ToolSequence
# ---------------------------------------------------------------------------

def test_sequence_add_remove():
    seq = ToolSequence(tool_id=1)
    op = OperationRecord("cylinder", params={"D": 40.0, "L": 30.0})
    seq.add(op)
    assert len(seq.operations) == 1
    seq.remove(0)
    assert len(seq.operations) == 0


def test_sequence_move():
    seq = ToolSequence(tool_id=1)
    seq.add(OperationRecord("face_turn"))
    seq.add(OperationRecord("cylinder"))
    seq.add(OperationRecord("chamfer"))
    seq.move(0, 2)    # move face_turn to end
    assert seq.operations[0].primitive_name == "cylinder"
    assert seq.operations[2].primitive_name == "face_turn"


def test_sequence_enabled_filter():
    seq = ToolSequence(tool_id=1)
    seq.add(OperationRecord("cylinder", enabled=True))
    seq.add(OperationRecord("chamfer",  enabled=False))
    assert len(seq.enabled_operations) == 1


# ---------------------------------------------------------------------------
# PartRecipe
# ---------------------------------------------------------------------------

def _sample_recipe() -> PartRecipe:
    recipe = PartRecipe(part_name="Test Shaft", notes="v1")
    recipe.stock = StockSpec(diameter=50.0, length=100.0, material_key="steel_45")
    seq1 = ToolSequence(
        tool_id=1,
        spindle_mode=SpindleMode.CSS,
        spindle_value=220.0,
        max_rpm=2000,
    )
    seq1.add(OperationRecord("face_turn", params={"depth": 1.0}))
    seq1.add(OperationRecord("cylinder",  params={"D": 40.0, "L": 50.0}))
    seq1.add(OperationRecord("chamfer",   params={"size": 2.0, "angle": 45.0}))
    seq2 = ToolSequence(tool_id=5, spindle_mode=SpindleMode.CONSTANT_RPM, spindle_value=400)
    seq2.add(OperationRecord("parting",   params={"x_target": 0.0}, direction=ToolDirection.EXTERNAL))
    recipe.add_sequence(seq1)
    recipe.add_sequence(seq2)
    return recipe


def test_recipe_all_tool_ids():
    recipe = _sample_recipe()
    assert recipe.all_tool_ids() == [1, 5]


def test_recipe_all_operations_flat():
    recipe = _sample_recipe()
    flat = recipe.all_operations()
    assert len(flat) == 4
    assert flat[0][2].primitive_name == "face_turn"
    assert flat[3][2].primitive_name == "parting"


def test_recipe_save_load_round_trip():
    recipe = _sample_recipe()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    try:
        recipe.save(path)
        loaded = PartRecipe.load(path)

        assert loaded.part_name == "Test Shaft"
        assert loaded.notes == "v1"
        assert abs(loaded.stock.diameter - 50.0) < 1e-9
        assert loaded.stock.material_key == "steel_45"
        assert len(loaded.tool_sequences) == 2

        seq1 = loaded.tool_sequences[0]
        assert seq1.tool_id == 1
        assert seq1.spindle_mode == SpindleMode.CSS
        assert abs(seq1.spindle_value - 220.0) < 1e-9
        assert seq1.max_rpm == 2000
        assert len(seq1.operations) == 3
        assert seq1.operations[1].primitive_name == "cylinder"
        assert abs(seq1.operations[1].params["D"] - 40.0) < 1e-9

        seq2 = loaded.tool_sequences[1]
        assert seq2.tool_id == 5
        assert seq2.spindle_mode == SpindleMode.CONSTANT_RPM
        assert seq2.operations[0].direction == ToolDirection.EXTERNAL
    finally:
        path.unlink(missing_ok=True)


def test_recipe_remove_sequence():
    recipe = _sample_recipe()
    recipe.remove_sequence(1)
    assert len(recipe.tool_sequences) == 1
    assert recipe.tool_sequences[0].tool_id == 1


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_builtin_materials_loaded,
        test_material_by_category,
        test_material_file_override,
        test_material_save_load_round_trip,
        test_operation_record_defaults,
        test_sequence_add_remove,
        test_sequence_move,
        test_sequence_enabled_filter,
        test_recipe_all_tool_ids,
        test_recipe_all_operations_flat,
        test_recipe_save_load_round_trip,
        test_recipe_remove_sequence,
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
