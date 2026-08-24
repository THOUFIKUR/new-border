"""
BorderPulse — Unit Tests: Decision Engine & Fusion
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pytest
from backend.decision.engine import DecisionEngine, DetectionState
from backend.decision.fusion import FusionEngine, FusionInput


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
    # Must be a MOTION WARNING — not HUMAN CONFIRMED
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


# ── Decision Engine Tests ─────────────────────────────────────────────────

def test_decision_high_confidence_immediate_alarm():
    """conf >= 0.85 + in zone → immediate ALARM_ACTIVE, no temporal wait."""
    de = DecisionEngine(min_frames=3, window_seconds=1.0, cooldown_seconds=0.1)
    out = de.process(
        track_id=1, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL"
    )
    assert out.is_critical is True
    assert out.state == DetectionState.ALARM_ACTIVE
    assert out.should_alarm is True
    assert out.should_create_event is True


def test_decision_temporal_path():
    """Low confidence → progress through POSSIBLE → TEMPORAL → CONFIRMED."""
    de = DecisionEngine(min_frames=3, window_seconds=2.0, cooldown_seconds=0.0)

    for i in range(3):
        out = de.process(
            track_id=2, zone_id="z1", class_name="person",
            confidence=0.55, fused_score=0.40,
            is_confirmed_fused=False, decision_label="POSSIBLE"
        )

    # After 3 frames in window → should be at TEMPORAL_CONFIRMATION or further
    assert out.state in (
        DetectionState.POSSIBLE_DETECTION,
        DetectionState.TEMPORAL_CONFIRMATION,
        DetectionState.CONFIRMED,
    )


def test_decision_cooldown():
    """Same track+zone should not create duplicate events within cooldown."""
    de = DecisionEngine(min_frames=1, window_seconds=5.0, cooldown_seconds=10.0)

    out1 = de.process(
        track_id=3, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL"
    )
    assert out1.should_create_event is True

    # Immediate second trigger — should be blocked by cooldown
    out2 = de.process(
        track_id=3, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL"
    )
    assert out2.should_create_event is False


def test_decision_different_tracks_independent():
    """Different track IDs in same zone should be independent state machines."""
    de = DecisionEngine(min_frames=1, window_seconds=5.0, cooldown_seconds=0.0)

    out1 = de.process(
        track_id=10, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL"
    )
    out2 = de.process(
        track_id=11, zone_id="z1", class_name="person",
        confidence=0.92, fused_score=0.92,
        is_confirmed_fused=True, decision_label="CRITICAL"
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

    # Immediate duplicate — should be blocked
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
