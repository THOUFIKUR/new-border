"""
BorderPulse — Decision Engine / Temporal Confirmation State Machine

State transitions:
  NO_DETECTION → POSSIBLE_DETECTION → TEMPORAL_CONFIRMATION → CONFIRMED
  → ALARM_ACTIVE → EVIDENCE_CAPTURE → EVENT_ACTIVE → EVENT_RESOLVED
  Also: FALSE_POSITIVE, ACKNOWLEDGED

One state machine per (track_id, zone_id) pair.
High-confidence visual intrusions skip temporal delay.
"""
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple, List
import backend.config as cfg

logger = logging.getLogger("borderpulse.decision")


class DetectionState(str, Enum):
    NO_DETECTION = "NO_DETECTION"
    POSSIBLE_DETECTION = "POSSIBLE_DETECTION"
    TEMPORAL_CONFIRMATION = "TEMPORAL_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    ALARM_ACTIVE = "ALARM_ACTIVE"
    EVIDENCE_CAPTURE = "EVIDENCE_CAPTURE"
    EVENT_ACTIVE = "EVENT_ACTIVE"
    EVENT_RESOLVED = "EVENT_RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"


@dataclass
class TrackState:
    track_id: Optional[int]
    zone_id: str
    state: DetectionState = DetectionState.NO_DETECTION
    frame_times: List[float] = field(default_factory=list)
    state_entered_at: float = field(default_factory=time.monotonic)
    last_detection_at: float = field(default_factory=time.monotonic)
    event_id: Optional[str] = None
    class_name: str = "person"
    peak_confidence: float = 0.0

    # Cooldown tracking
    alarm_triggered_at: Optional[float] = None

    def frames_in_window(self, window_seconds: float) -> int:
        now = time.monotonic()
        self.frame_times = [t for t in self.frame_times if now - t <= window_seconds]
        return len(self.frame_times)


@dataclass
class DecisionOutput:
    track_id: Optional[int]
    zone_id: str
    state: DetectionState
    previous_state: DetectionState
    state_changed: bool
    should_alarm: bool          # Trigger ESP32 buzzer
    should_create_event: bool   # Create new Supabase event
    should_capture: bool        # Start evidence capture
    is_critical: bool           # Immediate high-confidence intrusion
    confidence: float
    fused_score: float
    decision_label: str
    class_name: str
    timestamp: float = field(default_factory=time.time)


class DecisionEngine:
    """
    Per-track temporal confirmation and alarm state machine.
    Designed to be sensor/camera agnostic — only receives structured inputs.
    """

    def __init__(
        self,
        min_frames: int = 3,
        window_seconds: float = 1.0,
        cooldown_seconds: float = 10.0,
        human_high_confidence: float = 0.85,
    ):
        self.min_frames = min_frames
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.human_high_confidence = human_high_confidence

        # Key: (track_id, zone_id)
        self._tracks: Dict[Tuple, TrackState] = {}
        self._last_cleanup = time.monotonic()

    def update_config(self, min_frames: int, window_seconds: float,
                      cooldown_seconds: float, human_high_confidence: float):
        self.min_frames = min_frames
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.human_high_confidence = human_high_confidence

    def process(
        self,
        track_id: Optional[int],
        zone_id: str,
        class_name: str,
        confidence: float,
        fused_score: float,
        is_confirmed_fused: bool,
        decision_label: str,
    ) -> DecisionOutput:

        key = (track_id, zone_id)
        now = time.monotonic()

        if key not in self._tracks:
            self._tracks[key] = TrackState(
                track_id=track_id,
                zone_id=zone_id,
                class_name=class_name,
            )

        ts = self._tracks[key]
        ts.last_detection_at = now
        ts.peak_confidence = max(ts.peak_confidence, confidence)
        ts.frame_times.append(now)
        frames_in_window = ts.frames_in_window(self.window_seconds)

        prev_state = ts.state
        should_alarm = False
        should_create_event = False
        should_capture = False
        is_critical = False

        # ── INTRUSION ALARM PATH ──────────────────────────────────────────
        # Trigger alarm if person is detected in restricted zone by YOLO
        # OR if person is in restricted zone AND ground sensor is triggered
        if class_name == "person":
            is_critical = True
            if ts.state not in (
                DetectionState.ALARM_ACTIVE,
                DetectionState.EVENT_ACTIVE,
                DetectionState.EVIDENCE_CAPTURE,
            ):
                # Check cooldown
                if ts.alarm_triggered_at is None or (now - ts.alarm_triggered_at) >= self.cooldown_seconds:
                    ts.state = DetectionState.ALARM_ACTIVE
                    ts.alarm_triggered_at = now
                    should_alarm = True
                    should_create_event = True
                    should_capture = True
                    logger.info(f"[INTRUSION ALARM] Person detected in restricted zone {zone_id} conf={confidence:.2f}")

        else:
            # ── TEMPORAL PATH ──────────────────────────────────────────
            if ts.state == DetectionState.NO_DETECTION:
                ts.state = DetectionState.POSSIBLE_DETECTION
                ts.state_entered_at = now

            elif ts.state == DetectionState.POSSIBLE_DETECTION:
                if frames_in_window >= self.min_frames:
                    ts.state = DetectionState.TEMPORAL_CONFIRMATION
                    ts.state_entered_at = now

            elif ts.state == DetectionState.TEMPORAL_CONFIRMATION:
                if is_confirmed_fused or frames_in_window >= self.min_frames:
                    ts.state = DetectionState.CONFIRMED
                    ts.state_entered_at = now

            elif ts.state == DetectionState.CONFIRMED:
                if ts.alarm_triggered_at is None or (now - ts.alarm_triggered_at) >= self.cooldown_seconds:
                    ts.state = DetectionState.ALARM_ACTIVE
                    ts.alarm_triggered_at = now
                    should_alarm = class_name == "person"
                    should_create_event = True
                    should_capture = True
                    logger.info(f"[CONFIRMED] Track {track_id} zone={zone_id} score={fused_score:.2f}")

            elif ts.state == DetectionState.ALARM_ACTIVE:
                ts.state = DetectionState.EVIDENCE_CAPTURE
                ts.state_entered_at = now
                should_capture = True

            elif ts.state in (DetectionState.EVIDENCE_CAPTURE, DetectionState.EVENT_ACTIVE):
                pass  # Stay until event resolves

        state_changed = ts.state != prev_state

        # Cleanup stale tracks periodically
        if now - self._last_cleanup > 30.0:
            self._cleanup_stale(now)

        return DecisionOutput(
            track_id=track_id,
            zone_id=zone_id,
            state=ts.state,
            previous_state=prev_state,
            state_changed=state_changed,
            should_alarm=should_alarm,
            should_create_event=should_create_event,
            should_capture=should_capture,
            is_critical=is_critical,
            confidence=confidence,
            fused_score=fused_score,
            decision_label=decision_label,
            class_name=class_name,
        )

    def resolve_event(self, track_id: Optional[int], zone_id: str, resolution: str = "resolved"):
        key = (track_id, zone_id)
        if key in self._tracks:
            if resolution == "false_positive":
                self._tracks[key].state = DetectionState.FALSE_POSITIVE
            elif resolution == "acknowledged":
                self._tracks[key].state = DetectionState.ACKNOWLEDGED
            else:
                self._tracks[key].state = DetectionState.EVENT_RESOLVED
            logger.info(f"Track {track_id} zone={zone_id} → {resolution}")

    def get_all_states(self) -> List[dict]:
        return [
            {
                "track_id": ts.track_id,
                "zone_id": ts.zone_id,
                "state": ts.state.value,
                "class_name": ts.class_name,
                "peak_confidence": round(ts.peak_confidence, 3),
                "last_detection_at": ts.last_detection_at,
            }
            for ts in self._tracks.values()
        ]

    def _cleanup_stale(self, now: float):
        stale_keys = [
            k for k, ts in self._tracks.items()
            if now - ts.last_detection_at > 60.0
        ]
        for k in stale_keys:
            del self._tracks[k]
        self._last_cleanup = now
        if stale_keys:
            logger.debug(f"Cleaned up {len(stale_keys)} stale track states")
