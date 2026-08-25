"""
BorderPulse — Decision Engine / Temporal Confirmation State Machine

State transitions:
  NO_DETECTION → POSSIBLE_DETECTION → TEMPORAL_CONFIRMATION → CONFIRMED
  → ALARM_ACTIVE → EVIDENCE_CAPTURE → EVENT_ACTIVE → EVENT_RESOLVED
  Also: FALSE_POSITIVE, ACKNOWLEDGED

One state machine per (track_id, zone_id) pair.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HUMAN ALARM LOGIC (Phase 1 fix)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A person detection inside a restricted zone is NOT an automatic alarm.
It must pass through temporal confirmation:

  Frame 1 → person inside zone → valid → 1 / PERSON_CONFIRMATION_FRAMES
  Frame 2 → person inside zone → valid → 2 / PERSON_CONFIRMATION_FRAMES
  Frame 3 → person inside zone → valid → 3 / PERSON_CONFIRMATION_FRAMES
  Frame 4 → person inside zone → valid → 4 / PERSON_CONFIRMATION_FRAMES
                                            ↓
                                  CONFIRMED HUMAN → ALARM

Exceptions:
  - High-confidence fast path: conf >= YOLO_HUMAN_HIGH_CONFIDENCE (default 0.85)
    skips temporal delay because at this confidence level a misdetection is
    extremely unlikely and rapid response is operationally valuable.
    Fast path still requires: inside zone + class == person.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOUNDING BOX STABILITY (Phase 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Per-track bbox history is maintained.
Sudden large jumps (center position or size ratio) reset the temporal counter.
Thresholds are configurable — liberal enough to allow normal walking.
"""
import time
import logging
from collections import deque
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
class BBoxSnapshot:
    """Minimal bounding-box record for stability checking."""
    cx: float   # centre-x (normalised)
    cy: float   # centre-y (normalised)
    w: float    # width    (normalised)
    h: float    # height   (normalised)


@dataclass
class TrackState:
    track_id: Optional[int]
    zone_id: str
    state: DetectionState = DetectionState.NO_DETECTION
    # Timestamps of valid confirmations in the current window
    frame_times: List[float] = field(default_factory=list)
    # Running count of consecutive valid person confirmations
    person_confirm_count: int = 0
    state_entered_at: float = field(default_factory=time.monotonic)
    last_detection_at: float = field(default_factory=time.monotonic)
    event_id: Optional[str] = None
    class_name: str = "person"
    peak_confidence: float = 0.0
    alarm_triggered_at: Optional[float] = None
    # Bbox history for stability check (last N snapshots)
    bbox_history: deque = field(default_factory=lambda: deque(maxlen=5))

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
    is_critical: bool           # High-confidence fast-path intrusion
    confidence: float
    fused_score: float
    decision_label: str
    class_name: str
    person_confirm_count: int = 0       # Current confirmation count
    person_confirm_required: int = 0    # Required for alarm
    timestamp: float = field(default_factory=time.time)


class DecisionEngine:
    """
    Per-track temporal confirmation and alarm state machine.
    Designed to be sensor/camera agnostic — only receives structured inputs.

    For persons: requires PERSON_CONFIRMATION_FRAMES consecutive valid
    detections (same track, inside zone, stable bbox) before alarming.

    For other classes: uses TEMPORAL_MIN_FRAMES with the existing multi-state path.
    """

    def __init__(
        self,
        min_frames: int = 3,
        window_seconds: float = 2.0,
        cooldown_seconds: float = 10.0,
        human_high_confidence: float = 0.85,
        person_confirmation_frames: int = 4,
        bbox_max_center_jump: float = 0.25,
        bbox_max_size_ratio: float = 3.0,
    ):
        self.min_frames = min_frames
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.human_high_confidence = human_high_confidence
        self.person_confirmation_frames = person_confirmation_frames
        self.bbox_max_center_jump = bbox_max_center_jump
        self.bbox_max_size_ratio = bbox_max_size_ratio

        # Key: (track_id, zone_id)
        self._tracks: Dict[Tuple, TrackState] = {}
        self._last_cleanup = time.monotonic()

    def update_config(
        self,
        min_frames: int,
        window_seconds: float,
        cooldown_seconds: float,
        human_high_confidence: float,
        person_confirmation_frames: int = 4,
    ):
        self.min_frames = min_frames
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.human_high_confidence = human_high_confidence
        self.person_confirmation_frames = person_confirmation_frames

    # ── Bbox stability ────────────────────────────────────────────────────

    def _is_bbox_stable(self, ts: TrackState, new_bbox: Optional[dict]) -> bool:
        """
        Return True if the new bounding box is consistent with recent history.
        A sudden large jump resets person temporal confirmation.

        new_bbox: {"x1", "y1", "x2", "y2"} in normalised coords, or None.
        """
        if new_bbox is None:
            return True  # No bbox info — do not penalise

        cx = (new_bbox["x1"] + new_bbox["x2"]) / 2.0
        cy = (new_bbox["y1"] + new_bbox["y2"]) / 2.0
        w  = new_bbox["x2"] - new_bbox["x1"]
        h  = new_bbox["y2"] - new_bbox["y1"]

        if ts.bbox_history:
            prev = ts.bbox_history[-1]
            center_jump = ((cx - prev.cx) ** 2 + (cy - prev.cy) ** 2) ** 0.5
            if center_jump > self.bbox_max_center_jump:
                logger.debug(
                    f"[STABILITY] track={ts.track_id} center_jump={center_jump:.3f} "
                    f"> {self.bbox_max_center_jump} → reset"
                )
                ts.bbox_history.clear()
                return False

            if prev.w > 0 and prev.h > 0:
                w_ratio = max(w / prev.w, prev.w / w) if w > 0 else self.bbox_max_size_ratio + 1
                h_ratio = max(h / prev.h, prev.h / h) if h > 0 else self.bbox_max_size_ratio + 1
                if w_ratio > self.bbox_max_size_ratio or h_ratio > self.bbox_max_size_ratio:
                    logger.debug(
                        f"[STABILITY] track={ts.track_id} size_ratio w={w_ratio:.2f} h={h_ratio:.2f} → reset"
                    )
                    ts.bbox_history.clear()
                    return False

        ts.bbox_history.append(BBoxSnapshot(cx=cx, cy=cy, w=w, h=h))
        return True

    # ── Main processing ───────────────────────────────────────────────────

    def process(
        self,
        track_id: Optional[int],
        zone_id: str,
        class_name: str,
        confidence: float,
        fused_score: float,
        is_confirmed_fused: bool,
        decision_label: str,
        bbox_norm: Optional[dict] = None,
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
        person_confirm_count = 0
        person_confirm_required = self.person_confirmation_frames

        # ── PERSON ALARM PATH ─────────────────────────────────────────────
        # Persons must accumulate temporal confirmations.
        # Only after PERSON_CONFIRMATION_FRAMES valid consecutive confirmations
        # does the system declare a confirmed human intrusion and fire the alarm.
        #
        # Exception — HIGH-CONFIDENCE FAST PATH:
        #   If confidence >= human_high_confidence (default 0.85) the operator
        #   has a very strong visual signal. A single very confident detection
        #   inside a restricted zone is alarmed immediately. This is documented
        #   and intentional — at ≥0.85 the YOLO misdetection rate is very low.
        #   The fast path still requires: class==person AND inside_zone.
        if class_name == "person":
            # --- High-confidence fast path -----------------------------------
            if confidence >= self.human_high_confidence:
                is_critical = True
                person_confirm_count = self.person_confirmation_frames  # effectively "instant"
                logger.info(
                    f"[YOLO] PERSON confidence={confidence:.2f} track={track_id} "
                    f"→ HIGH-CONFIDENCE FAST PATH (>={self.human_high_confidence})"
                )
                if ts.state not in (
                    DetectionState.ALARM_ACTIVE,
                    DetectionState.EVENT_ACTIVE,
                    DetectionState.EVIDENCE_CAPTURE,
                ):
                    if ts.alarm_triggered_at is None or (now - ts.alarm_triggered_at) >= self.cooldown_seconds:
                        ts.state = DetectionState.ALARM_ACTIVE
                        ts.alarm_triggered_at = now
                        ts.person_confirm_count = self.person_confirmation_frames
                        should_alarm = True
                        should_create_event = True
                        should_capture = True
                        logger.info(
                            f"[DECISION] CONFIRMED_HUMAN (fast path) "
                            f"track={track_id} zone={zone_id} conf={confidence:.2f}"
                        )
                        logger.info(f"[BUZZER] ACTIVE — fast path conf={confidence:.2f}")

            # --- Standard 4-frame temporal path ------------------------------
            else:
                # Check bbox stability before counting this frame
                bbox_stable = self._is_bbox_stable(ts, bbox_norm)

                if not bbox_stable:
                    # Reset confirmation counter
                    ts.person_confirm_count = 0
                    if ts.state not in (
                        DetectionState.ALARM_ACTIVE,
                        DetectionState.EVENT_ACTIVE,
                        DetectionState.EVIDENCE_CAPTURE,
                    ):
                        ts.state = DetectionState.POSSIBLE_DETECTION
                    logger.debug(
                        f"[TEMPORAL] track={ts.track_id} bbox unstable → confirm reset"
                    )
                else:
                    # Only increment if not already in alarm states
                    if ts.state not in (
                        DetectionState.ALARM_ACTIVE,
                        DetectionState.EVENT_ACTIVE,
                        DetectionState.EVIDENCE_CAPTURE,
                    ):
                        ts.person_confirm_count += 1
                        count = ts.person_confirm_count
                        logger.info(
                            f"[TEMPORAL] track={track_id} confirmation={count}/{self.person_confirmation_frames} "
                            f"zone={zone_id} conf={confidence:.2f}"
                        )

                        if ts.state == DetectionState.NO_DETECTION:
                            ts.state = DetectionState.POSSIBLE_DETECTION
                            ts.state_entered_at = now

                        if count >= self.person_confirmation_frames:
                            # Check cooldown before firing alarm
                            if ts.alarm_triggered_at is None or (now - ts.alarm_triggered_at) >= self.cooldown_seconds:
                                ts.state = DetectionState.ALARM_ACTIVE
                                ts.alarm_triggered_at = now
                                should_alarm = True
                                should_create_event = True
                                should_capture = True
                                logger.info(
                                    f"[TEMPORAL] track={track_id} confirmation={count}/{self.person_confirmation_frames} "
                                    f"→ CONFIRMED"
                                )
                                logger.info(
                                    f"[DECISION] CONFIRMED_HUMAN "
                                    f"track={track_id} zone={zone_id} conf={confidence:.2f} "
                                    f"frames={count}"
                                )
                                logger.info(f"[BUZZER] ACTIVE — temporal confirmed")
                        elif count == self.person_confirmation_frames - 1:
                            ts.state = DetectionState.TEMPORAL_CONFIRMATION
                        elif count > 0:
                            ts.state = DetectionState.POSSIBLE_DETECTION

                person_confirm_count = ts.person_confirm_count

        # ── NON-PERSON TEMPORAL PATH ──────────────────────────────────────
        # Animals, vehicles, etc. go through multi-state confirmation.
        # Persons are NOT classified as human by radar/ground alone.
        else:
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
                    should_alarm = False  # Only persons trigger the buzzer
                    should_create_event = True
                    should_capture = True
                    logger.info(f"[CONFIRMED] Track {track_id} zone={zone_id} class={class_name} score={fused_score:.2f}")

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
            person_confirm_count=person_confirm_count,
            person_confirm_required=person_confirm_required,
        )

    def resolve_event(self, track_id: Optional[int], zone_id: str, resolution: str = "resolved"):
        key = (track_id, zone_id)
        if key in self._tracks:
            ts = self._tracks[key]
            ts.person_confirm_count = 0
            if resolution == "false_positive":
                ts.state = DetectionState.FALSE_POSITIVE
            elif resolution == "acknowledged":
                ts.state = DetectionState.ACKNOWLEDGED
            else:
                ts.state = DetectionState.EVENT_RESOLVED
            logger.info(f"Track {track_id} zone={zone_id} → {resolution}")

    def get_all_states(self) -> List[dict]:
        return [
            {
                "track_id": ts.track_id,
                "zone_id": ts.zone_id,
                "state": ts.state.value,
                "class_name": ts.class_name,
                "peak_confidence": round(ts.peak_confidence, 3),
                "person_confirm_count": ts.person_confirm_count,
                "person_confirm_required": self.person_confirmation_frames,
                "last_detection_at": ts.last_detection_at,
            }
            for ts in self._tracks.values()
        ]

    def get_track_confirmation(self, track_id: Optional[int], zone_id: str) -> dict:
        """Return temporal confirmation state for a specific track."""
        key = (track_id, zone_id)
        ts = self._tracks.get(key)
        if ts is None:
            return {"count": 0, "required": self.person_confirmation_frames, "state": "NO_DETECTION"}
        return {
            "count": ts.person_confirm_count,
            "required": self.person_confirmation_frames,
            "state": ts.state.value,
        }

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
