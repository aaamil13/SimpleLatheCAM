"""
Minimal smoke-test for the plug-in loader.

Verifies that:
  - All .py files in plugins/primitives/ are discovered
  - Each plug-in has a non-empty name, display_name and params_schema
  - No duplicate names are registered
  - default_params() returns values within declared min/max bounds
  - validate() returns None for default params against a generic context

Run with:  python -m pytest tests/ -v
or simply: python tests/test_plugin_loader.py
"""

import sys
from pathlib import Path

# Make sure the project root is on the path so imports resolve.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# PySide6 is required to import the plug-ins (they reference QPainter etc.
# at import time through type annotations).  If PySide6 is not available
# we mock the minimal surface needed by the annotations.
try:
    import PySide6  # noqa: F401
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False
    import types, unittest.mock as mock
    # Create minimal stubs so the TYPE_CHECKING imports don't blow up.
    pyside6 = types.ModuleType("PySide6")
    for sub in ("QtGui", "QtCore"):
        m = types.ModuleType(f"PySide6.{sub}")
        sys.modules[f"PySide6.{sub}"] = m
    sys.modules["PySide6"] = pyside6
    # Attach the names actually used in plug-in files.
    for name in ("QPainter", "QPen", "QColor", "QRect", "Qt"):
        setattr(sys.modules["PySide6.QtGui"], name, mock.MagicMock)
        setattr(sys.modules["PySide6.QtCore"], name, mock.MagicMock)

from domain.plugin_loader import PrimitivePluginLoader
from domain.primitive_base import ProfileContext


def make_context(**kwargs) -> ProfileContext:
    defaults = dict(
        cursor_x=50.0,
        cursor_z=0.0,
        stock_d=50.0,
        stock_l=150.0,
        segment_count=0,
        drilled_r=5.0,   # simulate a 10 mm starter hole for bore validation
        drilled_z=-50.0,
    )
    defaults.update(kwargs)
    return ProfileContext(**defaults)


def test_discovery():
    loader = PrimitivePluginLoader()
    loader.load(ROOT / "plugins" / "primitives")

    assert not loader.errors, f"Load errors: {loader.errors}"
    assert len(loader.names()) > 0, "No plug-ins were loaded"

    for p in loader.all():
        assert p.name,         f"{type(p)}: name is empty"
        assert p.display_name, f"{p.name}: display_name is empty"
        assert p.params_schema is not None, f"{p.name}: params_schema is None"

    print(f"  Loaded {len(loader.names())} plug-in(s): {loader.names()}")


def test_no_duplicates():
    loader = PrimitivePluginLoader()
    loader.load(ROOT / "plugins" / "primitives")
    names = loader.names()
    assert len(names) == len(set(names)), "Duplicate plug-in names detected"


def test_default_params_in_range():
    loader = PrimitivePluginLoader()
    loader.load(ROOT / "plugins" / "primitives")

    for p in loader.all():
        defaults = p.default_params()
        for spec in p.params_schema:
            val = defaults[spec.name]
            assert spec.min_val <= val <= spec.max_val, (
                f"{p.name}.{spec.name}: default {val} out of "
                f"[{spec.min_val}, {spec.max_val}]"
            )


def test_validate_defaults_ok():
    loader = PrimitivePluginLoader()
    loader.load(ROOT / "plugins" / "primitives")

    for p in loader.all():
        # Build a context that satisfies the primitive's minimum requirements
        ctx = make_context(segment_count=p.min_segments)
        result = p.validate(p.default_params(), ctx)
        assert result is None, (
            f"{p.name}.validate() returned error for default params: {result}"
        )


def test_by_category():
    loader = PrimitivePluginLoader()
    loader.load(ROOT / "plugins" / "primitives")
    groups = loader.by_category()
    assert isinstance(groups, dict)
    for cat, primitives in groups.items():
        assert len(primitives) > 0


if __name__ == "__main__":
    tests = [
        test_discovery,
        test_no_duplicates,
        test_default_params_in_range,
        test_validate_defaults_ok,
        test_by_category,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print()
    print(f"{'All tests passed.' if not failed else f'{failed} test(s) failed.'}")
    sys.exit(failed)
