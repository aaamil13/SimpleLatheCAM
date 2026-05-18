"""
Tests for EditorModel.get_profile_up_to(target_seq, target_op).

Verifies that the partial rebuild stops at the correct operation and that
the cursor position and segment count reflect only the operations up to
(and including) the target.
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.plugin_loader import PrimitivePluginLoader
from domain.profile import LatheProfile

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication(sys.argv)

from ui.editor_model import EditorModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRIMITIVES_DIR = ROOT / "plugins" / "primitives"


def _loader() -> PrimitivePluginLoader:
    ldr = PrimitivePluginLoader()
    ldr.load(PRIMITIVES_DIR)
    return ldr


def _model_with_ops(*names: str) -> EditorModel:
    ldr = _loader()
    model = EditorModel(ldr)
    model.new_recipe()
    for name in names:
        model.add_operation(name)
    return model


# ---------------------------------------------------------------------------
# Basic cursor-position checks
# ---------------------------------------------------------------------------

def test_up_to_op0_cursor_matches_single_op_profile():
    """
    get_profile_up_to(0, 0) on a two-op recipe must produce the same cursor
    position as a one-op recipe built with only the first primitive.
    """
    model = _model_with_ops("cylinder", "cylinder")

    partial = model.get_profile_up_to(0, 0)
    reference = _model_with_ops("cylinder").profile

    assert abs(partial.cursor_z - reference.cursor_z) < 1e-6
    assert abs(partial.cursor_x - reference.cursor_x) < 1e-6


def test_up_to_last_op_equals_full_profile():
    """
    get_profile_up_to(0, N-1) must match the fully-built profile.
    """
    model = _model_with_ops("cylinder", "cylinder", "cylinder")
    n = len(model.recipe.tool_sequences[0].operations)
    partial = model.get_profile_up_to(0, n - 1)

    assert abs(partial.cursor_z - model.profile.cursor_z) < 1e-6
    assert abs(partial.cursor_x - model.profile.cursor_x) < 1e-6


def test_up_to_op1_cursor_between_op0_and_full():
    """
    After two facing operations the Z cursor is deeper than after one.
    The partial profile for op1 must be deeper than op0 but same as full.
    """
    model = _model_with_ops("cylinder", "cylinder", "cylinder")
    p0 = model.get_profile_up_to(0, 0)
    p1 = model.get_profile_up_to(0, 1)
    p2 = model.get_profile_up_to(0, 2)

    assert p1.cursor_z <= p0.cursor_z, "op1 should advance Z further than op0"
    assert abs(p2.cursor_z - model.profile.cursor_z) < 1e-6


# ---------------------------------------------------------------------------
# Segment count grows monotonically
# ---------------------------------------------------------------------------

def test_segment_count_grows_with_op_index():
    """Each additional enabled op adds at least one segment."""
    model = _model_with_ops("cylinder", "cylinder", "cylinder")
    counts = [
        len(list(model.get_profile_up_to(0, i).segments()))
        for i in range(3)
    ]
    assert counts[0] > 0
    assert counts[1] >= counts[0]
    assert counts[2] >= counts[1]


# ---------------------------------------------------------------------------
# Disabled operations are skipped
# ---------------------------------------------------------------------------

def test_disabled_op_skipped_in_partial():
    """
    If op 1 is disabled, get_profile_up_to(0, 1) must equal get_profile_up_to(0, 0)
    because the disabled op contributes nothing.
    """
    model = _model_with_ops("cylinder", "cylinder", "cylinder")
    model.recipe.tool_sequences[0].operations[1].enabled = False
    model._mutated(0, 0)

    p_after_disabled = model.get_profile_up_to(0, 1)
    p_after_op0      = model.get_profile_up_to(0, 0)

    assert abs(p_after_disabled.cursor_z - p_after_op0.cursor_z) < 1e-6


# ---------------------------------------------------------------------------
# Out-of-range indices return full profile gracefully
# ---------------------------------------------------------------------------

def test_out_of_range_returns_full_profile():
    """
    If target indices exceed the recipe, get_profile_up_to should return
    the complete profile without raising an exception.
    """
    model = _model_with_ops("cylinder")
    result = model.get_profile_up_to(99, 99)
    assert result is not None
    assert abs(result.cursor_z - model.profile.cursor_z) < 1e-6


def test_empty_recipe_returns_blank_stock():
    """An empty recipe produces a profile with no segments."""
    model = EditorModel(_loader())
    result = model.get_profile_up_to(0, 0)
    assert list(result.segments()) == []
