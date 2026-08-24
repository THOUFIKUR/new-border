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
