"""
Tests for LatheProfile segment building, cursor tracking, and polygon export.
"""

import math
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from domain.profile import LatheProfile, LineSegment, ArcSegment, ArcDirection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return math.isclose(a, b, abs_tol=tol)


# ---------------------------------------------------------------------------
# Cursor tracking
# ---------------------------------------------------------------------------

def test_initial_cursor():
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    assert approx(p.cursor_x, 50.0)
    assert approx(p.cursor_z, 0.0)
    assert p.segment_count == 0


def test_cylinder_advances_z():
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_cylinder(d=50.0, length=30.0)
    assert approx(p.cursor_z, -30.0)
    assert approx(p.cursor_x, 50.0)


def test_cylinder_step_inserts_face_move():
    """Changing diameter within add_cylinder must insert a radial line first."""
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_cylinder(d=50.0, length=20.0)  # 1 segment
    p.add_cylinder(d=30.0, length=20.0)  # face move + cylinder = 2 more
    assert p.segment_count == 3
    # Second segment: radial face move at Z=-20
    face = p.to_gcode_segments()[1]
    assert isinstance(face, LineSegment)
    assert approx(face.z0, -20.0) and approx(face.z1, -20.0)
    assert approx(face.x0 * 2, 50.0)  # radius→diameter
    assert approx(face.x1 * 2, 30.0)


def test_taper_advances_both_axes():
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_taper(d_end=30.0, length=20.0)
    assert approx(p.cursor_x, 30.0)
    assert approx(p.cursor_z, -20.0)
    assert p.segment_count == 1
    seg = p.to_gcode_segments()[0]
    assert isinstance(seg, LineSegment)
    assert approx(seg.x0 * 2, 50.0)
    assert approx(seg.x1 * 2, 30.0)


def test_multiple_cylinders_accumulate_z():
    p = LatheProfile(stock_d=60.0, stock_l=200.0)
    p.add_cylinder(d=60.0, length=40.0)
    p.add_cylinder(d=60.0, length=40.0)  # same D — no face move
    assert approx(p.cursor_z, -80.0)
    assert p.segment_count == 2


def test_add_line_to():
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_line_to(d=30.0, z=-25.0)
    assert approx(p.cursor_x, 30.0)
    assert approx(p.cursor_z, -25.0)


# ---------------------------------------------------------------------------
# Fillet
# ---------------------------------------------------------------------------

def test_fillet_adds_arc():
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_cylinder(d=50.0, length=30.0)  # ends at Z=-30, D=50
    p.add_cylinder(d=30.0, length=20.0)  # face + cylinder; last seg ends at Z=-50
    p.add_fillet(radius=3.0)
    segs = p.to_gcode_segments()
    assert any(isinstance(s, ArcSegment) for s in segs), "Expected an ArcSegment"


def test_fillet_too_large_raises():
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_cylinder(d=50.0, length=2.0)  # only 2 mm long
    try:
        p.add_fillet(radius=5.0)        # radius > segment length → error
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Polygon export
# ---------------------------------------------------------------------------

def test_polygon_no_consecutive_duplicates():
    p = LatheProfile(stock_d=50.0, stock_l=100.0)
    p.add_cylinder(d=50.0, length=30.0)
    p.add_cylinder(d=30.0, length=20.0)
    pts = p.to_polygon()
    for i in range(len(pts) - 1):
        assert pts[i] != pts[i + 1], f"Duplicate point at index {i}: {pts[i]}"


def test_polygon_with_arc_has_more_points():
    p_no_arc = LatheProfile(stock_d=50.0, stock_l=100.0)
    p_no_arc.add_cylinder(d=50.0, length=30.0)

    p_arc = LatheProfile(stock_d=50.0, stock_l=100.0)
    p_arc.add_cylinder(d=50.0, length=30.0)
    p_arc.add_cylinder(d=30.0, length=20.0)
    p_arc.add_fillet(radius=2.0)

    assert len(p_arc.to_polygon(arc_resolution=16)) > len(p_no_arc.to_polygon())


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def test_stock_validation():
    try:
        LatheProfile(stock_d=0, stock_l=100)
        assert False, "Should raise for zero diameter"
    except ValueError:
        pass
    try:
        LatheProfile(stock_d=50, stock_l=-1)
        assert False, "Should raise for negative length"
    except ValueError:
        pass


def test_repr_contains_segment_count():
    p = LatheProfile(stock_d=40.0, stock_l=80.0)
    p.add_cylinder(d=40.0, length=20.0)
    r = repr(p)
    assert "segments=1" in r


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_initial_cursor,
        test_cylinder_advances_z,
        test_cylinder_step_inserts_face_move,
        test_taper_advances_both_axes,
        test_multiple_cylinders_accumulate_z,
        test_add_line_to,
        test_fillet_adds_arc,
        test_fillet_too_large_raises,
        test_polygon_no_consecutive_duplicates,
        test_polygon_with_arc_has_more_points,
        test_stock_validation,
        test_repr_contains_segment_count,
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
