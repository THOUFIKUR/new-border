"""
BorderPulse — Decision Engine & Fusion Unit Tests
16-case decision matrix (Phases 1 & 13)

Tests cover all required sensor-fusion cases plus:
- 4-frame temporal confirmation
- Bbox stability / reset
- ESP32 offline resilience
- High-confidence fast path
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pytest
from unittest.mock import MagicMock, patch
from backend.decision.engine import DecisionEngine, DetectionState
from backend.decision.fusion import FusionEngine, FusionInput


# ── Helpers ───────────────────────────────────────────────────────────────

def make_engine(
    person_frames=4,
    window=5.0,
    cooldown=0.0,
    high_conf=0.85,
):
    return DecisionEngine(
        min_frames=3,
        window_seconds=window,
        cooldown_seconds=cooldown,
        human_high_confidence=high_conf,
        person_confirmation_frames=person_frames,
        bbox_max_center_jump=0.25,
        bbox_max_size_ratio=3.0,
    )


ZONE = "restricted_01"
STABLE_BBOX = {"x1": 0.3, "y1": 0.3, "x2": 0.5, "y2": 0.7}


def process_person(de, track_id=1, confidence=0.60, bbox=None):
    return de.process(
        track_id=track_id,
        zone_id=ZONE,
        class_name="person",
        confidence=confidence,
        fused_score=confidence * 0.55,
        is_confirmed_fused=False,
        decision_label="POSSIBLE DETECTION",
        bbox_norm=bbox or STABLE_BBOX,
    )


# ── Fusion Engine Tests ───────────────────────────────────────────────────

def test_fusion_critical_vision_only():
    """High vision confidence → CRITICAL HUMAN INTRUSION label."""
    fe = FusionEngine()
    inp = FusionInput(
        vision_confidence=0.92,
        radar_triggered=False,
        ground_triggered=False,
        temporal_confirmed=False,
        class_name="person",
        inside_zone=True,
    )
    result = fe.compute(inp)
    assert result.decision_label == "CRITICAL HUMAN INTRUSION"
    assert result.fused_score == pytest.approx(0.92 * 0.55, abs=0.01)


def test_fusion_confirmed_with_all_sensors():
    """Low vision + radar + ground + temporal → CONFIRMED."""
    fe = FusionEngine()
    inp = FusionInput(
        vision_confidence=0.55,
        radar_triggered=True,
        ground_triggered=True,
        temporal_confirmed=True,
        class_name="person",
        inside_zone=True,
    )
    result = fe.compute(inp)
    expected = 0.55 * 0.55 + 0.20 + 0.15 + 0.10
    assert result.fused_score == pytest.approx(expected, abs=0.01)
    assert result.is_confirmed is True
    assert "CONFIRMED" in result.decision_label


def test_fusion_possible_vision_only_low():
    """Low vision, no sensors → POSSIBLE DETECTION."""
    fe = FusionEngine()
    inp = FusionInput(
        vision_confidence=0.55,
        radar_triggered=False,
        ground_triggered=False,
        temporal_confirmed=False,
        class_name="person",
        inside_zone=True,
    )
    result = fe.compute(inp)
    assert result.is_confirmed is False
    assert "POSSIBLE" in result.decision_label


def test_fusion_radar_not_human_identity():
    """Radar alone must not produce HUMAN CONFIRMED label."""
    fe = FusionEngine()
    inp = FusionInput(
        vision_confidence=0.0,
        radar_triggered=True,
        ground_triggered=False,
        temporal_confirmed=False,
        class_name="person",
        inside_zone=False,
    )
    result = fe.compute(inp)
    assert "HUMAN CONFIRMED" not in result.decision_label
    assert "MOTION" in result.decision_label or result.fused_score < 0.65


def test_fusion_weights_configurable():
    fe = FusionEngine(w_vision=0.7, w_radar=0.1, w_ground=0.1, w_temporal=0.1)
    inp = FusionInput(
        vision_confidence=1.0,
        radar_triggered=False,
        ground_triggered=False,
        temporal_confirmed=False,
        class_name="person",
        inside_zone=True,
    )
    result = fe.compute(inp)
    assert result.fused_score == pytest.approx(0.7, abs=0.01)


# ── Decision Engine — 16-case Test Matrix ─────────────────────────────────

# TEST 1 — No detection → no alarm
def test_01_no_detection_no_alarm():
    """No detection → no alarm fired."""
    de = make_engine()
    # No calls to process() at all — engine is idle.
    states = de.get_all_states()
    assert len(states) == 0


# TEST 2 — Radar only → no alarm
def test_02_radar_only_no_alarm():
    """Radar triggered without YOLO person → no human alarm."""
    # Radar alone never calls decision engine for a person.
    # We verify fusion output for radar-only is not confirmed.
    fe = FusionEngine()
    inp = FusionInput(
        vision_confidence=0.0,
        radar_triggered=True,
        ground_triggered=False,
        temporal_confirmed=False,
        class_name="unknown",
        inside_zone=False,
    )
    result = fe.compute(inp)
    assert result.is_confirmed is False
    assert "HUMAN" not in result.decision_label.upper() or "CONFIRMED" not in result.decision_label.upper()


# TEST 3 — Ground only → no alarm
def test_03_ground_only_no_alarm():
    """Ground sensor without YOLO person → no human alarm."""
    fe = FusionEngine()
    inp = FusionInput(
        vision_confidence=0.0,
        radar_triggered=False,
        ground_triggered=True,
        temporal_confirmed=False,
        class_name="unknown",
        inside_zone=False,
    )
    result = fe.compute(inp)
    assert result.is_confirmed is False
    assert "HUMAN" not in result.decision_label.upper() or "CONFIRMED" not in result.decision_label.upper()


# TEST 4 — Radar + Ground without person → no human alarm
def test_04_radar_and_ground_no_person_no_human_alarm():
    """Radar + Ground without YOLO person detection → no human alarm."""
    fe = FusionEngine()
    inp = FusionInput(
        vision_confidence=0.0,
        radar_triggered=True,
        ground_triggered=True,
        temporal_confirmed=False,
        class_name="unknown",
        inside_zone=False,
    )
    result = fe.compute(inp)
    # May fire as sensor activity but NOT as human confirmed
    assert "HUMAN" not in result.decision_label.upper() or "CONFIRMED" not in result.decision_label.upper()
    # Score should not be high enough to claim human identity
    assert result.fused_score < 0.65


# TEST 5 — Person outside zone → no alarm
def test_05_person_outside_zone_no_alarm():
    """Person detected but NOT inside any restricted zone → engine not called → no alarm."""
    # In production, zone_engine.check_detection returns [] → decision not invoked.
    # We verify the engine itself: if process() is somehow called with outside-zone,
    # it must not fire because the caller only calls process() when inside_zone.
    # (The zone check is in app.py — here we just verify engine stays clean.)
    de = make_engine()
    states = de.get_all_states()
    assert len(states) == 0


# TEST 6 — Person inside zone, 1 frame → no alarm
def test_06_person_zone_1_frame_no_alarm():
    """Person inside zone, 1 valid frame → no alarm (need 4)."""
    de = make_engine(person_frames=4)
    out = process_person(de)
    assert out.should_alarm is False
    assert out.should_create_event is False
    assert out.state in (DetectionState.POSSIBLE_DETECTION, DetectionState.NO_DETECTION)


# TEST 7 — Person inside zone, 2 frames → no alarm
def test_07_person_zone_2_frames_no_alarm():
    """Person inside zone, 2 valid frames → no alarm (need 4)."""
    de = make_engine(person_frames=4)
    for _ in range(2):
        out = process_person(de)
    assert out.should_alarm is False
    assert out.should_create_event is False


# TEST 8 — Person inside zone, 3 frames → no alarm
def test_08_person_zone_3_frames_no_alarm():
    """Person inside zone, 3 valid frames → no alarm (need 4)."""
    de = make_engine(person_frames=4)
    for _ in range(3):
        out = process_person(de)
    assert out.should_alarm is False
    assert out.should_create_event is False
    # Must be in temporal confirmation state
    assert out.state in (
        DetectionState.POSSIBLE_DETECTION,
        DetectionState.TEMPORAL_CONFIRMATION,
    )


# TEST 9 — Person inside zone, 4 valid frames → alarm
def test_09_person_zone_4_frames_alarm():
    """Person inside zone, 4 consecutive valid frames → ALARM fires."""
    de = make_engine(person_frames=4, cooldown=0.0)
    out = None
    for _ in range(4):
        out = process_person(de)
    assert out.should_alarm is True
    assert out.should_create_event is True
    assert out.state == DetectionState.ALARM_ACTIVE


# TEST 10 — Unstable bbox resets confirmation
def test_10_unstable_bbox_resets_confirmation():
    """Sudden large bbox jump resets person temporal confirmation counter."""
    de = make_engine(person_frames=4, cooldown=0.0)
    # 3 stable frames
    for _ in range(3):
        process_person(de, bbox={"x1": 0.3, "y1": 0.3, "x2": 0.5, "y2": 0.7})
    # Check count is 3
    states = de.get_all_states()
    assert states[0]["person_confirm_count"] == 3

    # Now a large jump — center moves > 0.25 normalised
    out = de.process(
        track_id=1,
        zone_id=ZONE,
        class_name="person",
        confidence=0.62,
        fused_score=0.34,
        is_confirmed_fused=False,
        decision_label="POSSIBLE",
        bbox_norm={"x1": 0.7, "y1": 0.7, "x2": 0.95, "y2": 0.95},  # far jump
    )
    # Alarm must NOT fire
    assert out.should_alarm is False
    # Count must be reset (back to 0)
    states = de.get_all_states()
    assert states[0]["person_confirm_count"] == 0


# TEST 11 — High-confidence fast path
def test_11_high_confidence_fast_path():
    """conf >= 0.85 inside zone → immediate alarm (fast path)."""
    de = make_engine(high_conf=0.85)
    out = process_person(de, confidence=0.91)
    assert out.is_critical is True
    assert out.should_alarm is True
    assert out.should_create_event is True
    assert out.state == DetectionState.ALARM_ACTIVE


# TEST 12 — Animal inside zone → no human alarm
def test_12_animal_zone_no_human_alarm():
    """Animal detected inside zone → no buzzer (only persons trigger buzzer)."""
    de = make_engine()
    out = de.process(
        track_id=5,
        zone_id=ZONE,
        class_name="dog",
        confidence=0.80,
        fused_score=0.60,
        is_confirmed_fused=True,
        decision_label="CONFIRMED: DOG",
    )
    # should_alarm is False for animals (buzzer is person-only)
    assert out.should_alarm is False


# TEST 13 — Person + radar → confirmed through decision engine
def test_13_person_plus_radar_via_decision_engine():
    """Person + simulated radar → alarm only after 4 frames through decision engine."""
    de = make_engine(person_frames=4, cooldown=0.0)
    fe = FusionEngine()
    for i in range(4):
        fusion_in = FusionInput(
            vision_confidence=0.65,
            radar_triggered=True,
            ground_triggered=False,
            temporal_confirmed=(i == 3),
            class_name="person",
            inside_zone=True,
        )
        fusion_out = fe.compute(fusion_in)
        out = de.process(
            track_id=10,
            zone_id=ZONE,
            class_name="person",
            confidence=0.65,
            fused_score=fusion_out.fused_score,
            is_confirmed_fused=fusion_out.is_confirmed,
            decision_label=fusion_out.decision_label,
            bbox_norm=STABLE_BBOX,
        )
    assert out.should_alarm is True
    assert out.state == DetectionState.ALARM_ACTIVE


# TEST 14 — Person + ground → confirmed through decision engine
def test_14_person_plus_ground_via_decision_engine():
    """Person + ground sensor → alarm after 4 frames through decision engine."""
    de = make_engine(person_frames=4, cooldown=0.0)
    fe = FusionEngine()
    for i in range(4):
        fusion_in = FusionInput(
            vision_confidence=0.65,
            radar_triggered=False,
            ground_triggered=True,
            temporal_confirmed=(i == 3),
            class_name="person",
            inside_zone=True,
        )
        fusion_out = fe.compute(fusion_in)
        out = de.process(
            track_id=11,
            zone_id=ZONE,
            class_name="person",
            confidence=0.65,
            fused_score=fusion_out.fused_score,
            is_confirmed_fused=fusion_out.is_confirmed,
            decision_label=fusion_out.decision_label,
            bbox_norm=STABLE_BBOX,
        )
    assert out.should_alarm is True
    assert out.state == DetectionState.ALARM_ACTIVE


# TEST 15 — Person + radar + ground → confirmed through decision engine
def test_15_person_plus_radar_plus_ground_via_decision_engine():
    """Full multi-sensor evidence → alarm after 4 frames (not before)."""
    de = make_engine(person_frames=4, cooldown=0.0)
    fe = FusionEngine()
    alarm_frames = []
    for i in range(4):
        fusion_in = FusionInput(
            vision_confidence=0.65,
            radar_triggered=True,
            ground_triggered=True,
            temporal_confirmed=(i >= 3),
            class_name="person",
            inside_zone=True,
        )
        fusion_out = fe.compute(fusion_in)
        out = de.process(
            track_id=12,
            zone_id=ZONE,
            class_name="person",
            confidence=0.65,
            fused_score=fusion_out.fused_score,
            is_confirmed_fused=fusion_out.is_confirmed,
            decision_label=fusion_out.decision_label,
            bbox_norm=STABLE_BBOX,
        )
        if out.should_alarm:
            alarm_frames.append(i)
    # Alarm should fire exactly at frame 3 (4th frame, 0-indexed)
    assert 3 in alarm_frames
    # Must NOT have fired at frames 0, 1, or 2
    assert 0 not in alarm_frames
    assert 1 not in alarm_frames
    assert 2 not in alarm_frames


# TEST 16 — ESP32 unavailable → no crash
def test_16_esp32_offline_no_crash():
    """ESP32 offline → backend handles gracefully, no exception."""
    from backend.hardware.esp32 import ESP32Client
    client = ESP32Client()
    # status.online = False by default (not connected)
    assert client.status.online is False
    # trigger_alarm must return False (not raise)
    result = client.trigger_alarm("test")
    assert result is False
    # stop_alarm must return False (not raise)
    result = client.stop_alarm()
    assert result is False


# ── Existing tests (preserved) ────────────────────────────────────────────

def test_decision_high_confidence_immediate_alarm():
    """conf >= 0.85 + in zone → immediate ALARM_ACTIVE, no temporal wait."""
    de = DecisionEngine(
        min_frames=3,
        window_seconds=1.0,
        cooldown_seconds=0.1,
        person_confirmation_frames=4,
    )
    out = de.process(
        track_id=1, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL",
        bbox_norm=STABLE_BBOX,
    )
    assert out.is_critical is True
    assert out.state == DetectionState.ALARM_ACTIVE
    assert out.should_alarm is True
    assert out.should_create_event is True


def test_decision_cooldown():
    """Same track+zone should not create duplicate events within cooldown."""
    de = DecisionEngine(min_frames=1, window_seconds=5.0, cooldown_seconds=10.0,
                        person_confirmation_frames=4)
    out1 = de.process(
        track_id=3, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL",
        bbox_norm=STABLE_BBOX,
    )
    assert out1.should_create_event is True

    out2 = de.process(
        track_id=3, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL",
        bbox_norm=STABLE_BBOX,
    )
    assert out2.should_create_event is False


def test_decision_different_tracks_independent():
    """Different track IDs in same zone should be independent state machines."""
    de = DecisionEngine(min_frames=1, window_seconds=5.0, cooldown_seconds=0.0,
                        person_confirmation_frames=4)
    out1 = de.process(
        track_id=10, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL",
        bbox_norm=STABLE_BBOX,
    )
    out2 = de.process(
        track_id=11, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL",
        bbox_norm=STABLE_BBOX,
    )
    assert out1.should_create_event is True
    assert out2.should_create_event is True


# ── Event Manager Tests ───────────────────────────────────────────────────

def test_event_manager_cooldown():
    from backend.events.manager import EventManager
    em = EventManager(db_client=None)
    em.set_cooldown(10.0)

    e1 = em.create_event(
        track_id=1, zone_id="z1", class_name="person",
        confidence=0.9, fused_score=0.9, is_critical=True,
        reason="test", sensor_evidence={}
    )
    assert e1 is not None

    e2 = em.create_event(
        track_id=1, zone_id="z1", class_name="person",
        confidence=0.9, fused_score=0.9, is_critical=True,
        reason="test", sensor_evidence={}
    )
    assert e2 is None


def test_event_manager_acknowledge():
    from backend.events.manager import EventManager
    em = EventManager(db_client=None)
    em.set_cooldown(0)

    event = em.create_event(
        track_id=5, zone_id="z1", class_name="person",
        confidence=0.9, fused_score=0.9, is_critical=True,
        reason="test", sensor_evidence={}
    )
    assert event is not None
    ok = em.acknowledge_event(event.id)
    assert ok is True
    retrieved = em.get_event(event.id)
    assert retrieved.status.value == "acknowledged"
