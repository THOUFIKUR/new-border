"""
BorderPulse — Unit Tests: Zone Engine (Point-in-Polygon)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from backend.vision.zones import ZonePoint, _ray_cast_pip, bottom_center, ZoneEngine, Zone


# ── Ray-casting tests ─────────────────────────────────────────────────────

SQUARE = [
    ZonePoint(0.1, 0.1),
    ZonePoint(0.9, 0.1),
    ZonePoint(0.9, 0.9),
    ZonePoint(0.1, 0.9),
]

TRIANGLE = [
    ZonePoint(0.5, 0.1),
    ZonePoint(0.9, 0.9),
    ZonePoint(0.1, 0.9),
]


def test_point_inside_square():
    assert _ray_cast_pip(0.5, 0.5, SQUARE) is True


def test_point_outside_square():
    assert _ray_cast_pip(0.05, 0.5, SQUARE) is False


def test_point_on_boundary_approx():
    # Near edge — should be inside for our use case
    assert _ray_cast_pip(0.11, 0.5, SQUARE) is True


def test_corner_outside():
    assert _ray_cast_pip(0.0, 0.0, SQUARE) is False


def test_point_inside_triangle():
    assert _ray_cast_pip(0.5, 0.7, TRIANGLE) is True


def test_point_outside_triangle():
    assert _ray_cast_pip(0.1, 0.1, TRIANGLE) is False


def test_degenerate_polygon_two_points():
    """Polygon with fewer than 3 points — always False."""
    two_pts = [ZonePoint(0.0, 0.0), ZonePoint(1.0, 1.0)]
    assert _ray_cast_pip(0.5, 0.5, two_pts) is False


def test_empty_polygon():
    assert _ray_cast_pip(0.5, 0.5, []) is False


# ── Bottom-center tests ───────────────────────────────────────────────────

def test_bottom_center_basic():
    bbox = {"x1": 0.2, "y1": 0.3, "x2": 0.6, "y2": 0.8}
    cx, cy = bottom_center(bbox)
    assert cx == pytest.approx(0.4, abs=1e-6)
    assert cy == pytest.approx(0.8, abs=1e-6)


def test_bottom_center_at_edge():
    bbox = {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
    cx, cy = bottom_center(bbox)
    assert cx == pytest.approx(0.5)
    assert cy == pytest.approx(1.0)


# ── ZoneEngine tests ──────────────────────────────────────────────────────

def test_zone_engine_load_and_check():
    engine = ZoneEngine()
    zones_raw = [
        {
            "id": "zone-1",
            "name": "Test Zone",
            "camera_id": None,
            "polygon_points": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.9},
                {"x": 0.1, "y": 0.9},
            ],
            "enabled": True,
            "zone_type": "restricted",
            "alert_on_classes": ["person"],
        }
    ]
    engine.load_zones(zones_raw)
    assert len(engine.get_zones()) == 1

    # Person at center → inside zone
    bbox_inside = {"x1": 0.4, "y1": 0.3, "x2": 0.6, "y2": 0.6}
    zones_triggered = engine.check_detection("person", bbox_inside)
    assert "zone-1" in zones_triggered

    # Person at top-left corner → outside zone
    bbox_outside = {"x1": 0.0, "y1": 0.0, "x2": 0.05, "y2": 0.05}
    zones_triggered = engine.check_detection("person", bbox_outside)
    assert len(zones_triggered) == 0


def test_zone_engine_disabled_zone():
    engine = ZoneEngine()
    zone = Zone(
        id="z1", name="Disabled",
        camera_id=None,
        polygon_points=[ZonePoint(0.1, 0.1), ZonePoint(0.9, 0.1),
                        ZonePoint(0.9, 0.9), ZonePoint(0.1, 0.9)],
        enabled=False,
    )
    engine.add_zone(zone)
    bbox = {"x1": 0.4, "y1": 0.3, "x2": 0.6, "y2": 0.6}
    # Disabled zone — should not trigger
    assert engine.check_detection("person", bbox) == []


def test_zone_class_filter():
    engine = ZoneEngine()
    zone = Zone(
        id="z2", name="Car-only",
        camera_id=None,
        polygon_points=[ZonePoint(0.1, 0.1), ZonePoint(0.9, 0.1),
                        ZonePoint(0.9, 0.9), ZonePoint(0.1, 0.9)],
        enabled=True,
        alert_on_classes=["car"],
    )
    engine.add_zone(zone)
    bbox = {"x1": 0.4, "y1": 0.3, "x2": 0.6, "y2": 0.6}
    # Person should not trigger a car-only zone
    assert engine.check_detection("person", bbox) == []
    # Car should trigger
    assert engine.check_detection("car", bbox) == ["z2"]


# ── False-alarm regression tests (feet-only for persons) ─────────────────

def _make_square_engine(zone_id: str = "sq") -> ZoneEngine:
    """Helper: engine with a square zone from (0.3, 0.3) to (0.7, 0.7)."""
    engine = ZoneEngine()
    zone = Zone(
        id=zone_id, name="Square",
        camera_id=None,
        polygon_points=[
            ZonePoint(0.3, 0.3), ZonePoint(0.7, 0.3),
            ZonePoint(0.7, 0.7), ZonePoint(0.3, 0.7),
        ],
        enabled=True,
        alert_on_classes=["person"],
    )
    engine.add_zone(zone)
    return engine


def test_person_feet_inside_zone_triggers():
    """Person with feet clearly inside zone → triggers."""
    engine = _make_square_engine()
    # bbox center at (0.5, 0.45), feet at y2=0.6 → feet inside zone
    bbox = {"x1": 0.4, "y1": 0.3, "x2": 0.6, "y2": 0.6}
    assert engine.check_detection("person", bbox) == ["sq"]


def test_representative_points_calculation():
    """Verify representative_points returns exact 9 points."""
    from backend.vision.zones import representative_points
    bbox = {"x1": 0.2, "y1": 0.4, "x2": 0.8, "y2": 0.8}
    pts = representative_points(bbox)
    assert len(pts) == 9
    assert pts[0] == (pytest.approx(0.2), pytest.approx(0.4))    # Top-Left
    assert pts[1] == (pytest.approx(0.5), pytest.approx(0.4))    # Top-Center
    assert pts[2] == (pytest.approx(0.8), pytest.approx(0.4))    # Top-Right
    assert pts[3] == (pytest.approx(0.2), pytest.approx(0.6))    # Center-Left
    assert pts[4] == (pytest.approx(0.5), pytest.approx(0.6))    # Center
    assert pts[5] == (pytest.approx(0.8), pytest.approx(0.6))    # Center-Right
    assert pts[6] == (pytest.approx(0.2), pytest.approx(0.8))    # Bottom-Left
    assert pts[7] == (pytest.approx(0.5), pytest.approx(0.8))    # Bottom-Center
    assert pts[8] == (pytest.approx(0.8), pytest.approx(0.8))    # Bottom-Right


def test_person_one_rep_point_inside_triggers():
    """Only 1 representative point (top-left) enters zone → person_inside_zone = TRUE."""
    engine = _make_square_engine()
    # Square zone: (0.3, 0.3) to (0.7, 0.7)
    # Bbox: x1=0.35, y1=0.35 (top-left inside zone). x2=0.85, y2=0.85 (outside zone).
    # Center = (0.6, 0.6) inside zone. Top-left (0.35, 0.35) inside zone.
    # At least 1 representative point inside -> triggers.
    bbox = {"x1": 0.35, "y1": 0.35, "x2": 0.85, "y2": 0.85}
    assert engine.check_detection("person", bbox) == ["sq"]


def test_person_bbox_touches_zone_no_rep_point_inside():
    """Person standing outside zone with bbox slightly touching zone edge but NO representative point inside → NO ALARM."""
    engine = _make_square_engine()
    # Square zone: (0.3, 0.3) to (0.7, 0.7)
    # Bbox: x1=0.10, y1=0.10, x2=0.299, y2=0.299
    # Bbox border is adjacent to 0.3, but none of the 9 representative points (corners/centers) cross >= 0.3
    bbox = {"x1": 0.10, "y1": 0.10, "x2": 0.299, "y2": 0.299}
    assert engine.check_detection("person", bbox) == []


def test_check_any_zone_person_rep_points():
    """check_any_zone with class_name='person' uses 9 representative points."""
    engine = _make_square_engine()
    bbox_in = {"x1": 0.4, "y1": 0.4, "x2": 0.6, "y2": 0.6}
    assert engine.check_any_zone(bbox_in, class_name="person") == ["sq"]

    bbox_out = {"x1": 0.0, "y1": 0.0, "x2": 0.1, "y2": 0.1}
    assert engine.check_any_zone(bbox_out, class_name="person") == []



def test_check_any_zone_unknown_uses_or_logic():
    """check_any_zone with unknown class uses OR logic (bottom-center or center)."""
    engine = _make_square_engine("sq")
    # Zone only allows "person" — check_any_zone bypasses class filter
    # Center at (0.5, 0.5) inside zone, feet at y2=0.80 outside zone.
    # OR logic → should trigger via center.
    bbox = {"x1": 0.4, "y1": 0.2, "x2": 0.6, "y2": 0.80}
    result = engine.check_any_zone(bbox, class_name="unknown")
    assert result == ["sq"], "check_any_zone with unknown class must use OR logic"
