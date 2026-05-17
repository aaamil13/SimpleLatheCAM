"""
Tests for MachineConfig: defaults, serialisation round-trip,
limit checks, and RPM capping.
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.machine import MachineConfig, AxisLimits, SafePositions


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

def test_default_creates_without_error():
    cfg = MachineConfig.default()
    assert cfg.max_spindle_rpm > 0
    assert cfg.limits.x_max > 0
    assert cfg.safe.x_clearance > 0


def test_approach_x_radius():
    cfg = MachineConfig.default()
    cfg.safe.x_clearance = 5.0
    result = cfg.approach_x_radius(stock_d=60.0)
    # stock radius 30 + clearance 5 = 35
    assert abs(result - 35.0) < 1e-9


# ---------------------------------------------------------------------------
# RPM capping
# ---------------------------------------------------------------------------

def test_cap_rpm_above_max():
    cfg = MachineConfig.default()
    cfg.max_spindle_rpm = 2000
    assert cfg.cap_rpm(5000) == 2000


def test_cap_rpm_below_min():
    cfg = MachineConfig.default()
    cfg.min_spindle_rpm = 80
    assert cfg.cap_rpm(20) == 80


def test_cap_rpm_within_range():
    cfg = MachineConfig.default()
    cfg.min_spindle_rpm = 50
    cfg.max_spindle_rpm = 3000
    assert cfg.cap_rpm(1200) == 1200


# ---------------------------------------------------------------------------
# Axis limits
# ---------------------------------------------------------------------------

def test_limits_contains():
    lim = AxisLimits(x_min=0, x_max=125, z_min=-350, z_max=5)
    assert lim.contains(50.0, -100.0)
    assert not lim.contains(200.0, -100.0)
    assert not lim.contains(50.0, -400.0)


def test_limits_check_returns_none_when_ok():
    cfg = MachineConfig.default()
    assert cfg.validate_position(50.0, -100.0) is None


def test_limits_check_returns_error_when_out():
    cfg = MachineConfig.default()
    cfg.limits.x_max = 100.0
    result = cfg.validate_position(150.0, -100.0)
    assert result is not None
    assert "X" in result


def test_limits_z_out_of_range():
    cfg = MachineConfig.default()
    cfg.limits.z_min = -300.0
    result = cfg.validate_position(50.0, -500.0)
    assert result is not None
    assert "Z" in result


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

def test_save_and_load_round_trip():
    cfg = MachineConfig(
        name="Test Lathe",
        max_spindle_rpm=1800,
        min_spindle_rpm=100,
        limits=AxisLimits(x_min=0, x_max=90, z_min=-250, z_max=3),
        safe=SafePositions(x_clearance=8.0, z_tool_change=60.0),
        chuck_diameter=125.0,
        coolant_available=True,
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)

    try:
        cfg.save(path)
        loaded = MachineConfig.load(path)

        assert loaded.name == "Test Lathe"
        assert loaded.max_spindle_rpm == 1800
        assert loaded.min_spindle_rpm == 100
        assert abs(loaded.limits.x_max - 90.0) < 1e-9
        assert abs(loaded.limits.z_min - (-250.0)) < 1e-9
        assert abs(loaded.safe.x_clearance - 8.0) < 1e-9
        assert abs(loaded.safe.z_tool_change - 60.0) < 1e-9
        assert abs(loaded.chuck_diameter - 125.0) < 1e-9
        assert loaded.coolant_available is True
    finally:
        path.unlink(missing_ok=True)


def test_default_json_template_loads():
    """Verify the bundled machine_default.json parses correctly."""
    template = ROOT / "data" / "machine_default.json"
    assert template.exists(), f"Template not found: {template}"
    cfg = MachineConfig.load(template)
    assert cfg.max_spindle_rpm > 0
    assert cfg.limits.x_max > 0


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_default_creates_without_error,
        test_approach_x_radius,
        test_cap_rpm_above_max,
        test_cap_rpm_below_min,
        test_cap_rpm_within_range,
        test_limits_contains,
        test_limits_check_returns_none_when_ok,
        test_limits_check_returns_error_when_out,
        test_limits_z_out_of_range,
        test_save_and_load_round_trip,
        test_default_json_template_loads,
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
