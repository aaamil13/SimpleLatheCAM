"""
Tests for MachineToolConfig and ToolOptimizer.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.machine_tools import InstalledTool, MachineToolConfig
from domain.tool import Tool, ToolDirection, ToolHolder, ToolInsert
from domain.tool_optimizer import (
    OpRequirement, ToolGroup, ToolOptimizer, can_tool_do,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tool(tid: int, direction: ToolDirection, nose_r: float, ic: float = 12.7) -> Tool:
    insert = ToolInsert(nose_radius=nose_r, ic_size=ic)
    holder = ToolHolder(direction=direction)
    return Tool(tool_id=tid, insert=insert, holder=holder)


def ext_rough(preferred=None) -> OpRequirement:
    return OpRequirement(
        "cylinder", ToolDirection.EXTERNAL,
        is_roughing=True, max_nose_radius=9999, min_nose_radius=0.4,
        preferred_tool_id=preferred,
    )

def ext_finish(preferred=None) -> OpRequirement:
    return OpRequirement(
        "chamfer", ToolDirection.EXTERNAL,
        is_roughing=False, max_nose_radius=0.4, min_nose_radius=0.0,
        preferred_tool_id=preferred,
    )

def int_rough() -> OpRequirement:
    return OpRequirement("cylinder", ToolDirection.INTERNAL, is_roughing=True)

def parting_op(blade_w=3.0) -> OpRequirement:
    return OpRequirement(
        "parting", ToolDirection.EXTERNAL,
        is_parting=True, blade_width=blade_w,
    )


# ---------------------------------------------------------------------------
# MachineToolConfig
# ---------------------------------------------------------------------------

def test_install_adds_to_available():
    cfg = MachineToolConfig(has_atc=True, turret_positions=8)
    cfg.install(InstalledTool(position=1, tool_id=1))
    assert cfg.is_installed(1)
    assert cfg.is_available(1)


def test_uninstall_keeps_available():
    cfg = MachineToolConfig()
    cfg.install(InstalledTool(position=1, tool_id=3))
    cfg.uninstall(1)
    assert not cfg.is_installed(3)
    assert cfg.is_available(3)   # still in inventory


def test_remove_available_uninstalls():
    cfg = MachineToolConfig(has_atc=True, turret_positions=4)
    cfg.install(InstalledTool(position=2, tool_id=5))
    cfg.remove_available(5)
    assert not cfg.is_available(5)
    assert not cfg.is_installed(5)


def test_position_of():
    cfg = MachineToolConfig(has_atc=True, turret_positions=4)
    cfg.install(InstalledTool(position=3, tool_id=7))
    assert cfg.position_of(7) == 3
    assert cfg.position_of(99) is None


def test_missing_from_available():
    cfg = MachineToolConfig()
    cfg.add_available(1)
    cfg.add_available(3)
    missing = cfg.missing_from_available([1, 3, 5])
    assert missing == [5]


def test_missing_from_installed():
    cfg = MachineToolConfig(has_atc=True, turret_positions=4)
    cfg.install(InstalledTool(position=1, tool_id=1))
    missing = cfg.missing_from_installed([1, 3])
    assert missing == [3]


def test_atc_position_overflow_raises():
    cfg = MachineToolConfig(has_atc=True, turret_positions=4)
    try:
        cfg.install(InstalledTool(position=5, tool_id=1))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_save_load_round_trip():
    cfg = MachineToolConfig(has_atc=True, turret_positions=8)
    cfg.install(InstalledTool(position=1, tool_id=1, offset_z=-125.3, note="roughing"))
    cfg.install(InstalledTool(position=3, tool_id=3, offset_z=-118.7))
    cfg.add_available(5)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    try:
        cfg.save(path)
        loaded = MachineToolConfig.load(path)
        assert loaded.has_atc
        assert loaded.turret_positions == 8
        assert loaded.is_installed(1) and loaded.is_installed(3)
        assert loaded.position_of(1) == 1
        assert abs(loaded.installed[1].offset_z - (-125.3)) < 1e-9
        assert loaded.installed[1].note == "roughing"
        assert 5 in loaded.available_ids
    finally:
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# can_tool_do
# ---------------------------------------------------------------------------

def test_can_tool_do_direction_mismatch():
    t = make_tool(1, ToolDirection.INTERNAL, 0.4)
    assert not can_tool_do(t, ext_rough())


def test_can_tool_do_nose_radius_ok():
    t = make_tool(1, ToolDirection.EXTERNAL, 0.8)
    assert can_tool_do(t, ext_rough())


def test_can_tool_do_nose_radius_too_large_for_finish():
    t = make_tool(1, ToolDirection.EXTERNAL, 0.8)
    assert not can_tool_do(t, ext_finish())


def test_can_tool_do_parting_blade_match():
    t = make_tool(5, ToolDirection.EXTERNAL, 0.2, ic=3.0)
    assert can_tool_do(t, parting_op(blade_w=3.0))


def test_can_tool_do_parting_blade_mismatch():
    t = make_tool(5, ToolDirection.EXTERNAL, 0.2, ic=4.0)
    assert not can_tool_do(t, parting_op(blade_w=3.0))


# ---------------------------------------------------------------------------
# ToolOptimizer
# ---------------------------------------------------------------------------

def test_optimizer_empty():
    opt = ToolOptimizer([])
    result = opt.optimize([])
    assert result.groups == []
    assert result.tool_changes == 0


def test_optimizer_single_op():
    tools = [make_tool(1, ToolDirection.EXTERNAL, 0.8)]
    opt = ToolOptimizer(tools)
    result = opt.optimize([ext_rough()])
    assert len(result.groups) == 1
    assert result.groups[0].tool_id == 1
    assert result.tool_changes == 0


def test_optimizer_groups_compatible():
    """Roughing (R=0.8) can also do another roughing → 1 group, 0 changes."""
    tools = [make_tool(1, ToolDirection.EXTERNAL, 0.8)]
    opt = ToolOptimizer(tools)
    result = opt.optimize([ext_rough(), ext_rough()])
    assert len(result.groups) == 1
    assert result.tool_changes == 0


def test_optimizer_forces_change_for_finish():
    """
    Roughing op requires min_nose_radius=0.6 (high chip load).
    T1 (R=0.8) qualifies for roughing but not finishing (R > 0.4 max).
    T3 (R=0.4) qualifies for finishing but NOT roughing (R < 0.6 min).
    → optimizer must use T1 for rough, T3 for finish = 2 groups, 1 change.
    """
    tools = [
        make_tool(1, ToolDirection.EXTERNAL, 0.8),
        make_tool(3, ToolDirection.EXTERNAL, 0.4),
    ]
    rough = OpRequirement(
        "cylinder", ToolDirection.EXTERNAL,
        is_roughing=True, min_nose_radius=0.6, max_nose_radius=9999,
    )
    opt = ToolOptimizer(tools)
    result = opt.optimize([rough, ext_finish()])
    assert len(result.groups) == 2
    assert result.tool_changes == 1
    assert result.groups[0].tool_id == 1
    assert result.groups[1].tool_id == 3


def test_optimizer_greedy_prefers_longer_run():
    """T1 (R=0.8) covers [rough, rough]; T3 (R=0.4) covers [rough, rough, finish].
    Optimizer should prefer T3 because it covers more ops."""
    tools = [
        make_tool(1, ToolDirection.EXTERNAL, 0.8),
        make_tool(3, ToolDirection.EXTERNAL, 0.4),
    ]
    opt = ToolOptimizer(tools)
    ops = [ext_rough(), ext_rough(), ext_finish()]
    result = opt.optimize(ops)
    # T3 (R=0.4) satisfies roughing (min_nose_radius=0.4) AND finishing
    assert len(result.groups) == 1
    assert result.groups[0].tool_id == 3
    assert result.tool_changes == 0


def test_optimizer_preferred_tool_honoured():
    """User explicitly requests T1 for roughing; optimizer must respect it."""
    tools = [
        make_tool(1, ToolDirection.EXTERNAL, 0.8),
        make_tool(3, ToolDirection.EXTERNAL, 0.4),
    ]
    opt = ToolOptimizer(tools)
    result = opt.optimize([ext_rough(preferred=1)])
    assert result.groups[0].tool_id == 1


def test_optimizer_warns_no_tool():
    opt = ToolOptimizer([])   # no tools available
    result = opt.optimize([ext_rough()])
    assert len(result.warnings) == 1
    assert not result.is_feasible


def test_validate_recipe_tools():
    tools = [make_tool(1, ToolDirection.EXTERNAL, 0.8)]
    opt = ToolOptimizer(tools)
    warnings = opt.validate_recipe_tools([1, 3, 5])
    assert len(warnings) == 2   # T3 and T5 missing


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_install_adds_to_available,
        test_uninstall_keeps_available,
        test_remove_available_uninstalls,
        test_position_of,
        test_missing_from_available,
        test_missing_from_installed,
        test_atc_position_overflow_raises,
        test_save_load_round_trip,
        test_can_tool_do_direction_mismatch,
        test_can_tool_do_nose_radius_ok,
        test_can_tool_do_nose_radius_too_large_for_finish,
        test_can_tool_do_parting_blade_match,
        test_can_tool_do_parting_blade_mismatch,
        test_optimizer_empty,
        test_optimizer_single_op,
        test_optimizer_groups_compatible,
        test_optimizer_forces_change_for_finish,
        test_optimizer_greedy_prefers_longer_run,
        test_optimizer_preferred_tool_honoured,
        test_optimizer_warns_no_tool,
        test_validate_recipe_tools,
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
