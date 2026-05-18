"""
Tests for segment tagging in EditorModel._rebuild() and insert_at().

Verifies:
  - Each segment gets the correct (seq_idx, op_idx) tag after rebuild
  - insert_at() inserts a new op and shifts following tags correctly
  - remove_selected() removes op and the remaining segments get new tags
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.plugin_loader import PrimitivePluginLoader
from domain.recipe import OperationRecord, PartRecipe, ToolSequence
from domain.tool import ToolDirection

# EditorModel requires a QApplication
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
    """Create an EditorModel with one ToolSequence containing named primitives."""
    ldr = _loader()
    model = EditorModel(ldr)
    model.new_recipe()
    for name in names:
        model.add_operation(name)
    return model


def _tags(model: EditorModel) -> list[tuple[int, int] | None]:
    return [s.tag for s in model.profile.segments()]


# ---------------------------------------------------------------------------
# Tag correctness after rebuild
# ---------------------------------------------------------------------------

def test_single_op_tags_all_zero():
    """All segments from the only operation must have tag (0, 0)."""
    model = _model_with_ops("cylinder")
    tags = _tags(model)
    assert len(tags) > 0
    assert all(t == (0, 0) for t in tags), f"unexpected tags: {tags}"


def test_two_ops_distinct_tags():
    """Two successive operations produce distinct tags (0,0) and (0,1)."""
    model = _model_with_ops("cylinder", "cylinder")
    tags = set(_tags(model))
    assert (0, 0) in tags
    assert (0, 1) in tags


def test_three_ops_all_tags_present():
    """Three operations → tags (0,0), (0,1), (0,2)."""
    model = _model_with_ops("cylinder", "cylinder", "cylinder")
    tags = set(_tags(model))
    assert tags == {(0, 0), (0, 1), (0, 2)}


def test_tags_stable_after_noop_param_update():
    """Updating a param triggers a rebuild; tags must remain the same."""
    model = _model_with_ops("cylinder", "cylinder")
    tags_before = set(_tags(model))
    model.select(0, 0)
    op = model.selected_operation()
    model.update_params(dict(op.params))   # identical params — just triggers rebuild
    tags_after = set(_tags(model))
    assert tags_before == tags_after


# ---------------------------------------------------------------------------
# insert_at
# ---------------------------------------------------------------------------

def test_insert_at_beginning_shifts_tags():
    """
    Before insert: ops = [facing(0,0), facing(0,1)]
    After insert at (0,0):  ops = [facing(0,0), facing(0,1), facing(0,2)]
    The newly inserted op takes tag (0,0); old ops shift to (0,1) and (0,2).
    """
    model = _model_with_ops("cylinder", "cylinder")
    model.insert_at(0, 0, "cylinder", ToolDirection.EXTERNAL)
    tags = set(_tags(model))
    assert (0, 0) in tags
    assert (0, 1) in tags
    assert (0, 2) in tags


def test_insert_at_appends_new_tag():
    """insert_at past the end behaves as append and adds the expected tag."""
    model = _model_with_ops("cylinder")
    op_count_before = len(model.recipe.tool_sequences[0].operations)
    model.insert_at(0, op_count_before, "cylinder", ToolDirection.EXTERNAL)
    tags = set(_tags(model))
    assert (0, 0) in tags
    assert (0, 1) in tags


# ---------------------------------------------------------------------------
# remove_selected
# ---------------------------------------------------------------------------

def test_remove_first_op_retags_remaining():
    """
    After removing op 0 from a two-op sequence, the surviving op must have
    tag (0, 0), not (0, 1).
    """
    model = _model_with_ops("cylinder", "cylinder")
    model.select(0, 0)
    model.remove_selected()
    tags = set(_tags(model))
    assert tags == {(0, 0)}, f"expected {{(0,0)}}, got {tags}"


def test_remove_second_op_keeps_first_tag():
    """Removing the last op leaves only op 0 tagged as (0,0)."""
    model = _model_with_ops("cylinder", "cylinder")
    model.select(0, 1)
    model.remove_selected()
    tags = set(_tags(model))
    assert tags == {(0, 0)}


def test_remove_all_ops_yields_no_tags():
    """Removing all operations leaves no segments (no tags)."""
    model = _model_with_ops("cylinder")
    model.select(0, 0)
    model.remove_selected()
    assert _tags(model) == []


# ---------------------------------------------------------------------------
# Disabled operations are skipped in tags
# ---------------------------------------------------------------------------

def test_disabled_op_reduces_tag_count():
    """
    Disabling one of two operations halves the number of distinct tags.
    The surviving op is re-indexed as ei=0 and gets tag (0, 0).
    """
    model = _model_with_ops("cylinder", "cylinder")
    tags_both = set(_tags(model))
    assert len(tags_both) == 2   # both enabled → (0,0) and (0,1)

    model.recipe.tool_sequences[0].operations[0].enabled = False
    model._mutated(0, 0)
    tags_one = set(_tags(model))
    assert len(tags_one) == 1    # only one enabled op → single tag (0,0)
    assert (0, 0) in tags_one    # surviving op is now ei=0
