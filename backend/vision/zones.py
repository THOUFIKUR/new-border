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


def representative_points(bbox: dict) -> List[tuple]:
    """
    Returns the 9 representative points (normalized 0.0-1.0) of a bounding box:
    1. top-left
    2. top-center
    3. top-right
    4. center-left
    5. center
    6. center-right
    7. bottom-left
    8. bottom-center
    9. bottom-right
    """
    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    return [
        (x1, y1),  # 1. top-left
        (cx, y1),  # 2. top-center
        (x2, y1),  # 3. top-right
        (x1, cy),  # 4. center-left
        (cx, cy),  # 5. center
        (x2, cy),  # 6. center-right
        (x1, y2),  # 7. bottom-left
        (cx, y2),  # 8. bottom-center
        (x2, y2),  # 9. bottom-right
    ]



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


def top_center(bbox: dict) -> tuple:
    """
    Returns the top-center point (normalized) of a bounding box (head/upper body).
    """
    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    cx = (x1 + x2) / 2.0
    cy = y1
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

    def get_zones(self, camera_id: Optional[str] = None) -> List[Zone]:
        if camera_id:
            return [z for z in self._zones.values() if not z.camera_id or z.camera_id == camera_id]
        return list(self._zones.values())

    def check_detection(self, class_name: str, bbox_norm: dict, track_id: Optional[int] = None, camera_id: Optional[str] = None) -> List[str]:
        """
        Check if a detection is inside any enabled zone.
        Only evaluates zones matching the specified camera_id (or unassigned zones).

        PERSON CLASS: Inside if ANY of the 9 representative points is inside the polygon.
        ALL OTHER CLASSES: OR logic — bottom-center OR center OR top-center.
        """
        px_b, py_b = bottom_center(bbox_norm)
        triggered = []
        for zone in self._zones.values():
            if not zone.enabled:
                continue
            if camera_id and zone.camera_id and zone.camera_id != camera_id:
                continue
            if class_name not in zone.alert_on_classes:
                continue
            if len(zone.polygon_points) < 3:
                continue

            if class_name == "person":
                pts = representative_points(bbox_norm)
                in_zone = any(_ray_cast_pip(px, py, zone.polygon_points) for px, py in pts)
            else:
                px_c, py_c = center_point(bbox_norm)
                px_t, py_t = top_center(bbox_norm)
                in_zone = (
                    _ray_cast_pip(px_b, py_b, zone.polygon_points)
                    or _ray_cast_pip(px_c, py_c, zone.polygon_points)
                    or _ray_cast_pip(px_t, py_t, zone.polygon_points)
                )

            logger.debug(
                f"[ZONE] camera={camera_id} track={track_id} representative_points=9 inside={in_zone}"
            )
            if in_zone:
                triggered.append(zone.id)
        return triggered

    def check_any_zone(self, bbox_norm: dict, class_name: str = "unknown", camera_id: Optional[str] = None) -> List[str]:
        """
        Check against all enabled zones matching camera_id regardless of class filter.
        """
        px_b, py_b = bottom_center(bbox_norm)
        triggered = []
        for zone in self._zones.values():
            if not zone.enabled or len(zone.polygon_points) < 3:
                continue
            if camera_id and zone.camera_id and zone.camera_id != camera_id:
                continue
            if class_name == "person":
                pts = representative_points(bbox_norm)
                in_zone = any(_ray_cast_pip(px, py, zone.polygon_points) for px, py in pts)
            else:
                px_c, py_c = center_point(bbox_norm)
                px_t, py_t = top_center(bbox_norm)
                in_zone = (
                    _ray_cast_pip(px_b, py_b, zone.polygon_points)
                    or _ray_cast_pip(px_c, py_c, zone.polygon_points)
                    or _ray_cast_pip(px_t, py_t, zone.polygon_points)
                )
            if in_zone:
                triggered.append(zone.id)
        return triggered

    def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone by ID. Returns True if found and removed, False if not found."""
        if zone_id in self._zones:
            del self._zones[zone_id]
            return True
        return False

    def to_frontend_list(self, camera_id: Optional[str] = None) -> List[dict]:
        return [
            {
                "id": z.id,
                "name": z.name,
                "camera_id": z.camera_id or "CAM-01",
                "enabled": z.enabled,
                "zone_type": z.zone_type,
                "polygon_points": [{"x": p.x, "y": p.y} for p in z.polygon_points],
                "alert_on_classes": z.alert_on_classes,
            }
            for z in self._zones.values()
            if not camera_id or not z.camera_id or z.camera_id == camera_id
        ]
