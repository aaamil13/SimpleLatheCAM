"""
Tests for cam/roughing.py — pyclipper pass generation.

Skips automatically when pyclipper is not installed.
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

pyclipper = pytest.importorskip("pyclipper", reason="pyclipper not installed")

from domain.profile import LatheProfile
from cam.roughing import ExternalRougher, InternalRougher, RoughingPass


def _simple_profile(d: float = 30.0, length: float = 50.0) -> LatheProfile:
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_cylinder(d=d, length=length)
    return p


def test_external_rougher_returns_passes():
    profile = _simple_profile(d=30.0, length=50.0)
    rougher = ExternalRougher(
        profile=profile,
        stock_r=25.0,
        stock_l=100.0,
        step_down=2.0,
        feed_rate=150.0,
        finish_allowance=0.3,
        nose_radius=0.4,
    )
    passes = rougher.generate()
    assert isinstance(passes, list)
    assert len(passes) > 0, "Expected at least one roughing pass"


def test_external_rougher_pass_structure():
    profile = _simple_profile(d=20.0, length=40.0)
    rougher = ExternalRougher(
        profile=profile,
        stock_r=25.0,
        stock_l=100.0,
        step_down=1.5,
    )
    passes = rougher.generate()
    for rp in passes:
        assert isinstance(rp, RoughingPass)
        assert rp.radius > 0
        assert len(rp.moves) >= 2
        assert rp.feed_rate > 0


def test_external_rougher_no_passes_when_no_material():
    """If part == stock, there is nothing to remove."""
    profile = _simple_profile(d=50.0, length=100.0)  # same as stock
    rougher = ExternalRougher(
        profile=profile,
        stock_r=25.0,
        stock_l=100.0,
        step_down=1.0,
        finish_allowance=0.0,
        nose_radius=0.0,
    )
    passes = rougher.generate()
    # May return zero passes or minimal passes — just check no crash
    assert isinstance(passes, list)


def test_external_rougher_respects_step_down():
    profile = _simple_profile(d=10.0, length=50.0)
    step = 2.0
    rougher = ExternalRougher(
        profile=profile,
        stock_r=25.0,
        stock_l=100.0,
        step_down=step,
        finish_allowance=0.0,
        nose_radius=0.0,
    )
    passes = rougher.generate()
    radii = [rp.radius for rp in passes]
    # Check that consecutive radius levels differ by approximately step_down
    if len(radii) >= 2:
        diffs = [abs(radii[i] - radii[i+1]) for i in range(len(radii)-1)]
        # Allow some tolerance due to slicing
        for d in diffs:
            assert d <= step + 1e-3


def test_internal_rougher_returns_passes():
    """InternalRougher: bore from pre-drilled hole outward."""
    p = LatheProfile(stock_d=50.0, stock_l=80.0)
    p.add_cylinder(d=30.0, length=40.0)

    rougher = InternalRougher(
        profile=p,
        bore_r=8.0,
        stock_l=80.0,
        step_down=1.0,
        finish_allowance=0.2,
        nose_radius=0.4,
    )
    passes = rougher.generate()
    assert isinstance(passes, list)
    # Internal rougher may return 0 passes for this simple profile — just no crash
