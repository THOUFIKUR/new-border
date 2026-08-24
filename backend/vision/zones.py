"""
BorderPulse — Restricted Zone Engine
Point-in-polygon using ray-casting (no shapely required).
Zones are stored as normalized coordinates (0.0–1.0).
"""
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import backend.config as cfg

logger = logging.getLogger("borderpulse.zones")


@dataclass
class ZonePoint:
    x: float  # 0.0–1.0
    y: float  # 0.0–1.0


@dataclass
class Zone:
    id: str
    name: str
    camera_id: Optional[str]
    polygon_points: List[ZonePoint]
    enabled: bool = True
    zone_type: str = "restricted"
    alert_on_classes: List[str] = field(default_factory=lambda: ["person"])


def _ray_cast_pip(px: float, py: float, polygon: List[ZonePoint]) -> bool:
    """
    Ray-casting point-in-polygon test.
    Returns True if (px, py) is inside polygon.
    Works with normalized coordinates.
    """
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i].x, polygon[i].y
        xj, yj = polygon[j].x, polygon[j].y
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def bottom_center(bbox: dict) -> tuple:
    """
    Returns the bottom-center point (normalized) of a bounding box.
    bbox: {"x1": float, "y1": float, "x2": float, "y2": float}
    """
    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    cx = (x1 + x2) / 2.0
    cy = y2  # bottom
    return cx, cy


def center_point(bbox: dict) -> tuple:
    """
    Returns the center point (normalized) of a bounding box.
    """
    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    return cx, cy


class ZoneEngine:
    """
    Manages restricted zones and performs point-in-polygon checks.
    Zones are loaded from Supabase on startup and can be refreshed.
    """

    def __init__(self):
        self._zones: Dict[str, Zone] = {}
        self._last_loaded: float = 0.0

    def load_zones(self, zones_raw: List[dict]):
        """Load zones from Supabase rows."""
        self._zones.clear()
        for row in zones_raw:
            try:
                pts = [ZonePoint(x=p["x"], y=p["y"]) for p in row.get("polygon_points", [])]
                z = Zone(
                    id=str(row["id"]),
                    name=row["name"],
                    camera_id=row.get("camera_id"),
                    polygon_points=pts,
                    enabled=bool(row.get("enabled", True)),
                    zone_type=row.get("zone_type", "restricted"),
                    alert_on_classes=row.get("alert_on_classes", ["person"]),
                )
                self._zones[z.id] = z
            except Exception as e:
                logger.warning(f"Failed to load zone {row.get('id')}: {e}")
        self._last_loaded = time.monotonic()
        logger.info(f"Loaded {len(self._zones)} zones")

    def add_zone(self, zone: Zone):
        self._zones[zone.id] = zone

    def remove_zone(self, zone_id: str):
        self._zones.pop(zone_id, None)

    def update_zone(self, zone: Zone):
        self._zones[zone.id] = zone

    def get_zones(self) -> List[Zone]:
        return list(self._zones.values())

    def check_detection(self, class_name: str, bbox_norm: dict) -> List[str]:
        """
        Check if a detection's bottom-center or center point is inside any enabled zone.
        bbox_norm: {"x1", "y1", "x2", "y2"} in 0.0–1.0 normalized coordinates.
        Returns list of zone IDs where the detection is inside.
        """
        px_b, py_b = bottom_center(bbox_norm)
        px_c, py_c = center_point(bbox_norm)
        triggered = []
        for zone in self._zones.values():
            if not zone.enabled:
                continue
            if class_name not in zone.alert_on_classes:
                continue
            if len(zone.polygon_points) < 3:
                continue
            if _ray_cast_pip(px_b, py_b, zone.polygon_points) or _ray_cast_pip(px_c, py_c, zone.polygon_points):
                triggered.append(zone.id)
        return triggered

    def check_any_zone(self, bbox_norm: dict) -> List[str]:
        """Check against all enabled zones regardless of class filter."""
        px_b, py_b = bottom_center(bbox_norm)
        px_c, py_c = center_point(bbox_norm)
        triggered = []
        for zone in self._zones.values():
            if not zone.enabled or len(zone.polygon_points) < 3:
                continue
            if _ray_cast_pip(px_b, py_b, zone.polygon_points) or _ray_cast_pip(px_c, py_c, zone.polygon_points):
                triggered.append(zone.id)
        return triggered

    def to_frontend_list(self) -> List[dict]:
        return [
            {
                "id": z.id,
                "name": z.name,
                "enabled": z.enabled,
                "zone_type": z.zone_type,
                "polygon_points": [{"x": p.x, "y": p.y} for p in z.polygon_points],
                "alert_on_classes": z.alert_on_classes,
            }
            for z in self._zones.values()
        ]
