"""
BorderPulse — Event Manager
Creates, tracks, and resolves events.
Implements cooldown and deduplication by (track_id, zone_id).
Writes to Supabase events table.
"""
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from backend.database.supabase_client import SupabaseClient

logger = logging.getLogger("borderpulse.events")


class EventSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class EventType(str, Enum):
    HUMAN_INTRUSION = "human_intrusion"
    ANIMAL = "animal"
    BIRD = "bird"
    VEHICLE = "vehicle"
    GROUP_ACTIVITY = "group_activity"
    ABNORMAL_ACTIVITY = "abnormal_activity"
    CAMERA_BLOCKED = "camera_blocked"
    LOW_VISIBILITY = "low_visibility"
    SENSOR_TRIGGER = "sensor_trigger"
    SYSTEM_ERROR = "system_error"
    TEST = "test"


@dataclass
class Event:
    id: str
    event_code: str
    event_type: EventType
    severity: EventSeverity
    status: EventStatus
    confidence: float
    zone_id: Optional[str]
    camera_id: Optional[str]
    track_id: Optional[int]
    reason: str
    metadata: dict
    started_at: float
    ended_at: Optional[float] = None
    supabase_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_code": self.event_code,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "confidence": round(self.confidence, 3),
            "zone_id": self.zone_id,
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "reason": self.reason,
            "metadata": self.metadata,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "supabase_id": self.supabase_id,
        }


def _classify_event(class_name: str, is_critical: bool, fused_score: float) -> tuple:
    """Returns (event_type, severity)."""
    if class_name == "person":
        if is_critical:
            return EventType.HUMAN_INTRUSION, EventSeverity.CRITICAL
        elif fused_score >= 0.65:
            return EventType.HUMAN_INTRUSION, EventSeverity.HIGH
        else:
            return EventType.HUMAN_INTRUSION, EventSeverity.MEDIUM
    elif class_name == "bird":
        return EventType.BIRD, EventSeverity.LOW
    elif class_name in ("cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"):
        return EventType.ANIMAL, EventSeverity.LOW
    elif class_name in ("car", "motorcycle", "bus", "truck", "bicycle"):
        return EventType.VEHICLE, EventSeverity.MEDIUM
    else:
        return EventType.HUMAN_INTRUSION, EventSeverity.INFO


class EventManager:
    """
    Creates and manages security events.
    Deduplicates by (track_id, zone_id) with cooldown.
    """

    def __init__(self, db_client=None, camera_id: Optional[str] = None):
        self._db = db_client
        self._camera_id = camera_id
        self._active_events: Dict[str, Event] = {}  # id → Event
        self._track_zone_last_event: Dict[tuple, float] = {}  # (track_id, zone_id) → time
        self._cooldown = 10.0
        self._event_counter = 0

    def set_cooldown(self, seconds: float):
        self._cooldown = seconds

    def set_camera_id(self, camera_id: str):
        self._camera_id = camera_id

    def create_event(
        self,
        track_id: Optional[int],
        zone_id: Optional[str],
        class_name: str,
        confidence: float,
        fused_score: float,
        is_critical: bool,
        reason: str,
        sensor_evidence: dict,
    ) -> Optional[Event]:
        """Create a new event if not in cooldown for this track/zone."""
        key = (track_id, zone_id or "")
        now = time.time()

        # Cooldown deduplication
        last = self._track_zone_last_event.get(key, 0.0)
        if now - last < self._cooldown:
            return None

        self._track_zone_last_event[key] = now
        self._event_counter += 1

        event_type, severity = _classify_event(class_name, is_critical, fused_score)
        event_id = str(uuid.uuid4())
        event_code = f"EVT-{int(now)}-{self._event_counter:04d}"

        event = Event(
            id=event_id,
            event_code=event_code,
            event_type=event_type,
            severity=severity,
            status=EventStatus.ACTIVE,
            confidence=confidence,
            zone_id=zone_id,
            camera_id=self._camera_id,
            track_id=track_id,
            reason=reason,
            metadata={
                "fused_score": fused_score,
                "is_critical": is_critical,
                "sensor_evidence": sensor_evidence,
                "class_name": class_name,
            },
            started_at=now,
        )

        self._active_events[event_id] = event
        logger.info(f"[EVENT] {event_code} type={event_type.value} severity={severity.value} "
                    f"track={track_id} zone={zone_id} conf={confidence:.2f}")

        # Write to Supabase asynchronously (fire and forget)
        if self._db:
            self._write_to_db(event)

        return event

    def acknowledge_event(self, event_id: str) -> bool:
        event = self._active_events.get(event_id)
        if event:
            event.status = EventStatus.ACKNOWLEDGED
            if self._db:
                self._update_db_status(event.supabase_id, "acknowledged")
            return True
        return False

    def resolve_event(self, event_id: str) -> bool:
        event = self._active_events.get(event_id)
        if event:
            event.status = EventStatus.RESOLVED
            event.ended_at = time.time()
            if self._db:
                self._update_db_status(event.supabase_id, "resolved")
            return True
        return False

    def mark_false_positive(self, event_id: str) -> bool:
        event = self._active_events.get(event_id)
        if event:
            event.status = EventStatus.FALSE_POSITIVE
            if self._db:
                self._update_db_status(event.supabase_id, "false_positive")
            return True
        return False

    def get_active_events(self) -> List[Event]:
        return [e for e in self._active_events.values()
                if e.status == EventStatus.ACTIVE]

    def get_all_events(self) -> List[Event]:
        return list(self._active_events.values())

    def get_event(self, event_id: str) -> Optional[Event]:
        return self._active_events.get(event_id)

    def get_event_count_today(self) -> int:
        midnight = time.time() - (time.time() % 86400)
        return sum(1 for e in self._active_events.values() if e.started_at >= midnight)

    # ── DB operations ────────────────────────────────────────────────────

    def _write_to_db(self, event: Event):
        try:
            row = {
                "id": event.id,
                "event_code": event.event_code,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "status": event.status.value,
                "trigger_source": "vision",
                "confidence": event.confidence,
                "zone_id": event.zone_id,
                "camera_id": event.camera_id,
                "reason": event.reason,
                "metadata": event.metadata,
            }
            result = self._db.table("events").insert(row).execute()
            if result.data:
                event.supabase_id = result.data[0]["id"]
        except Exception as e:
            logger.error(f"Failed to write event to Supabase: {e}")

    def _update_db_status(self, supabase_id: Optional[str], status: str):
        if not supabase_id:
            return
        try:
            self._db.table("events").update({"status": status}).eq("id", supabase_id).execute()
        except Exception as e:
            logger.error(f"Failed to update event status: {e}")
