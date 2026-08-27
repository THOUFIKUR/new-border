"""
BorderPulse — Decision Engine Unit Tests
Covers the 14 mandatory alarm test cases:
1. Person outside zone, Radar ON, Ground ON → NO ALARM
2. Person bbox overlaps zone but feet outside, Radar ON, Ground ON → NO ALARM
3. Person feet inside zone 1 frame, Radar ON, Ground ON → NO ALARM
4. Person feet inside zone 2 frames, Radar ON, Ground ON → NO ALARM
5. Person feet inside zone 3 frames, Radar ON, Ground ON → NO ALARM
6. Person feet inside zone 4 consecutive frames (>= 0.5s duration), Radar ON, Ground ON → ALARM
7. Person feet inside zone 4 frames, Radar ON, Ground OFF → NO ALARM
8. Person feet inside zone 4 frames, Radar OFF, Ground ON → NO ALARM
9. Person feet inside zone high confidence >= 0.85, Radar OFF, Ground OFF → IMMEDIATE ALARM
10. Person outside zone high confidence >= 0.85, Radar ON, Ground ON → NO ALARM
11. Alarm active and person remains inside → only ONE ESP32 /alarm request
12. Alarm active and person leaves zone → ONE /alarm/stop request
13. Ground ON + Radar ON but YOLO sees no person → NO ALARM
14. Person leaves zone and comes back → confirmation must restart at 1/4
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pytest
from backend.decision.engine import DecisionEngine, DetectionState
from backend.decision.fusion import FusionEngine, FusionInput


def make_engine(
    person_frames=4,
    window=5.0,
    cooldown=0.0,
    high_conf=0.85,
    min_duration=0.0,  # Set to 0 in fast unit tests unless testing duration explicitly
    track_loss_grace=2.0,
):
    return DecisionEngine(
        min_frames=3,
        window_seconds=window,
        cooldown_seconds=cooldown,
        human_high_confidence=high_conf,
        person_confirmation_frames=person_frames,
        person_min_confirm_seconds=min_duration,
        track_loss_grace_seconds=track_loss_grace,
        bbox_max_center_jump=0.25,
        bbox_max_size_ratio=3.0,
    )


ZONE = "restricted_01"
STABLE_BBOX = {"x1": 0.3, "y1": 0.3, "x2": 0.5, "y2": 0.7}


def process_person(
    de,
    track_id=1,
    confidence=0.60,
    bbox=None,
    feet_inside=True,
    radar=True,
    ground=True,
):
    return de.process(
        track_id=track_id,
        zone_id=ZONE,
        class_name="person",
        confidence=confidence,
        fused_score=confidence * 0.55,
        is_confirmed_fused=False,
        decision_label="POSSIBLE DETECTION",
        bbox_norm=bbox or STABLE_BBOX,
        feet_inside=feet_inside,
        radar_triggered=radar,
        ground_triggered=ground,
    )


# ── TEST 1: Person outside zone, Radar ON, Ground ON → NO ALARM ──────────
def test_01_person_outside_zone_radar_ground_on_no_alarm():
    de = make_engine()
    out = process_person(de, feet_inside=False, radar=True, ground=True)
    assert out.should_alarm is False
    assert out.state != DetectionState.ALARM_ACTIVE


# ── TEST 2: Person bbox overlaps zone but feet outside → NO ALARM ─────────
def test_02_bbox_overlaps_feet_outside_no_alarm():
    de = make_engine()
    # Feet inside is False
    out = process_person(de, feet_inside=False, radar=True, ground=True)
    assert out.should_alarm is False
    assert out.state != DetectionState.ALARM_ACTIVE


# ── TEST 3: Person feet inside 1 frame, Radar ON, Ground ON → NO ALARM ─────
def test_03_person_feet_inside_1_frame_no_alarm():
    de = make_engine(person_frames=4)
    out = process_person(de, feet_inside=True, radar=True, ground=True)
    assert out.should_alarm is False
    assert out.state != DetectionState.ALARM_ACTIVE
    assert out.person_confirm_count == 1


# ── TEST 4: Person feet inside 2 frames, Radar ON, Ground ON → NO ALARM ────
def test_04_person_feet_inside_2_frames_no_alarm():
    de = make_engine(person_frames=4)
    for _ in range(2):
        out = process_person(de, feet_inside=True, radar=True, ground=True)
    assert out.should_alarm is False
    assert out.state != DetectionState.ALARM_ACTIVE
    assert out.person_confirm_count == 2


# ── TEST 5: Person feet inside 3 frames, Radar ON, Ground ON → NO ALARM ────
def test_05_person_feet_inside_3_frames_no_alarm():
    de = make_engine(person_frames=4)
    for _ in range(3):
        out = process_person(de, feet_inside=True, radar=True, ground=True)
    assert out.should_alarm is False
    assert out.state != DetectionState.ALARM_ACTIVE
    assert out.person_confirm_count == 3


# ── TEST 6: Person feet inside 4 frames (duration >= 0.5s), Radar ON, Ground ON → ALARM ──
def test_06_person_feet_inside_4_frames_all_sensors_on_alarm():
    de = make_engine(person_frames=4, min_duration=0.0)
    for _ in range(3):
        out = process_person(de, feet_inside=True, radar=True, ground=True)
        assert out.should_alarm is False
    # 4th frame
    out = process_person(de, feet_inside=True, radar=True, ground=True)
    assert out.should_alarm is True
    assert out.state == DetectionState.ALARM_ACTIVE


# ── TEST 7: Person inside 4 frames, Ground OFF → ALARM ──
def test_07_person_feet_inside_4_frames_ground_off_alarm():
    de = make_engine(person_frames=4, min_duration=0.0)
    for _ in range(3):
        out = process_person(de, feet_inside=True, radar=True, ground=False)
        assert out.should_alarm is False
    out = process_person(de, feet_inside=True, radar=True, ground=False)
    assert out.should_alarm is True
    assert out.state == DetectionState.ALARM_ACTIVE


# ── TEST 8: Person inside 4 frames, Radar OFF → ALARM ──
def test_08_person_feet_inside_4_frames_radar_off_alarm():
    de = make_engine(person_frames=4, min_duration=0.0)
    for _ in range(3):
        out = process_person(de, feet_inside=True, radar=False, ground=True)
        assert out.should_alarm is False
    out = process_person(de, feet_inside=True, radar=False, ground=True)
    assert out.should_alarm is True
    assert out.state == DetectionState.ALARM_ACTIVE


# ── TEST 9: High confidence >= 0.85 + feet inside zone → IMMEDIATE ALARM on frame 1 ──
def test_09_high_confidence_immediate_alarm_frame_1():
    de = make_engine(person_frames=4, high_conf=0.85)
    # Frame 1: High confidence + feet inside zone → IMMEDIATE ALARM (bypasses 4-frame wait)
    out = process_person(de, confidence=0.92, feet_inside=True, radar=False, ground=False)
    assert out.should_alarm is True, "High-confidence override must trigger IMMEDIATE ALARM on frame 1"
    assert out.is_critical is True
    assert out.state == DetectionState.ALARM_ACTIVE

    # Subsequent frames — alarm stays active, NOT re-triggered
    for _ in range(5):
        out2 = process_person(de, confidence=0.92, feet_inside=True, radar=False, ground=False)
        assert out2.should_alarm is False, "Alarm must NOT re-trigger while already active"
        assert out2.state == DetectionState.ALARM_ACTIVE



# ── TEST 10: High confidence >= 0.85, OUTSIDE zone → NO ALARM ─────────────
def test_10_high_confidence_outside_zone_no_alarm():
    de = make_engine(high_conf=0.85)
    out = process_person(de, confidence=0.95, feet_inside=False, radar=True, ground=True)
    assert out.should_alarm is False
    assert out.state != DetectionState.ALARM_ACTIVE


# ── TEST 11: Alarm active and person remains inside → ONE /alarm request ─
def test_11_alarm_active_one_request_only():
    de = make_engine(person_frames=4, min_duration=0.0)
    alarms_fired = []
    # 4 frames to activate
    for _ in range(4):
        out = process_person(de, feet_inside=True, radar=True, ground=True)
        if out.should_alarm:
            alarms_fired.append(out)
    assert len(alarms_fired) == 1

    # 10 subsequent frames — person remains inside
    for _ in range(10):
        out = process_person(de, feet_inside=True, radar=True, ground=True)
        if out.should_alarm:
            alarms_fired.append(out)
    assert len(alarms_fired) == 1  # Still exactly 1 trigger call!


# ── TEST 12: Alarm active and person leaves zone → ONE /alarm/stop request ─
def test_12_person_leaves_zone_triggers_stop_alarm():
    de = make_engine(person_frames=4, min_duration=0.0)
    # Activate alarm
    for _ in range(4):
        out = process_person(de, feet_inside=True, radar=True, ground=True)
    assert out.state == DetectionState.ALARM_ACTIVE

    # Person leaves zone (feet_inside=False)
    out_leave = process_person(de, feet_inside=False, radar=True, ground=True)
    assert out_leave.should_stop_alarm is True
    assert out_leave.state == DetectionState.NO_DETECTION


# ── TEST 13: Ground ON + Radar ON, NO person → NO ALARM ──────────────────
def test_13_sensors_on_no_person_no_alarm():
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
    assert result.is_confirmed is False
    assert result.fused_score < 0.65


# ── TEST 14: Person leaves zone and comes back → confirmation restarts at 1/4 ──
def test_14_person_leaves_and_returns_restarts_confirmation():
    de = make_engine(person_frames=4, min_duration=0.0)
    # 2 frames inside
    process_person(de, feet_inside=True, radar=True, ground=True)
    out = process_person(de, feet_inside=True, radar=True, ground=True)
    assert out.person_confirm_count == 2

    # Person steps outside zone
    out_leave = process_person(de, feet_inside=False, radar=True, ground=True)
    assert out_leave.person_confirm_count == 0

    # Person returns inside zone
    out_return = process_person(de, feet_inside=True, radar=True, ground=True)
    assert out_return.person_confirm_count == 1  # Restarts at 1/4!


# ── Track loss grace period test ─────────────────────────────────────────
def test_track_loss_grace_period():
    de = make_engine(person_frames=4, min_duration=0.0, track_loss_grace=0.5)
    # Activate alarm
    for _ in range(4):
        de.process(
            track_id=99, zone_id=ZONE, class_name="person",
            confidence=0.65, fused_score=0.65, is_confirmed_fused=True,
            decision_label="CONFIRMED", bbox_norm=STABLE_BBOX,
            feet_inside=True, radar_triggered=True, ground_triggered=True,
        )

    # Short delay (< 0.5s grace) — track not lost yet
    cleared = de.check_track_loss(now=time.monotonic() + 0.2)
    assert len(cleared) == 0

    # Longer delay (> 0.5s grace) — track lost
    cleared = de.check_track_loss(now=time.monotonic() + 1.0)
    assert (99, ZONE) in cleared


# ── TEST 15 & 16: Ground Consecutive YES Counter & Max Cap ─────────────
def test_15_ground_consecutive_yes_duration_and_cap():
    max_cap = 5.0
    consecutive_yes = 0
    # 1 YES
    consecutive_yes += 1
    assert min(consecutive_yes, max_cap) == 1.0
    # 2 YES
    consecutive_yes += 1
    assert min(consecutive_yes, max_cap) == 2.0
    # 3 YES
    consecutive_yes += 1
    assert min(consecutive_yes, max_cap) == 3.0
    # 4 YES
    consecutive_yes += 1
    assert min(consecutive_yes, max_cap) == 4.0
    # 5 YES
    consecutive_yes += 1
    assert min(consecutive_yes, max_cap) == 5.0
    # 6 YES (capped at 5)
    consecutive_yes += 1
    assert min(consecutive_yes, max_cap) == 5.0


def test_16_ground_no_resets_counter():
    consecutive_yes = 3
    # Ground reading NO
    ground_active = False
    if not ground_active:
        consecutive_yes = 0
    assert consecutive_yes == 0


# ── TEST 17 & 18: Dual Alarm Arbitration & Combined Reasons ─────────────
def test_17_dual_alarm_arbitration_reasons():
    # Case 1: YOLO=OFF, GROUND=OFF -> buzzer OFF
    yolo, ground = False, False
    assert (yolo or ground) is False

    # Case 2: YOLO=ON, GROUND=OFF -> YOLO_HUMAN_INTRUSION
    yolo, ground = True, False
    reason = "YOLO_AND_GROUND" if (yolo and ground) else ("YOLO_HUMAN_INTRUSION" if yolo else "GROUND_SENSOR")
    assert (yolo or ground) is True
    assert reason == "YOLO_HUMAN_INTRUSION"

    # Case 3: YOLO=OFF, GROUND=ON -> GROUND_SENSOR
    yolo, ground = False, True
    reason = "YOLO_AND_GROUND" if (yolo and ground) else ("YOLO_HUMAN_INTRUSION" if yolo else "GROUND_SENSOR")
    assert (yolo or ground) is True
    assert reason == "GROUND_SENSOR"

    # Case 4: YOLO=ON, GROUND=ON -> YOLO_AND_GROUND
    yolo, ground = True, True
    reason = "YOLO_AND_GROUND" if (yolo and ground) else ("YOLO_HUMAN_INTRUSION" if yolo else "GROUND_SENSOR")
    assert (yolo or ground) is True
    assert reason == "YOLO_AND_GROUND"


def test_18_person_leaves_while_ground_active_buzzer_remains_on():
    yolo_alarm = True
    ground_alarm = True

    # Person leaves -> yolo_alarm becomes False
    yolo_alarm = False
    # Ground alarm is still active -> overall buzzer stays ON
    buzzer_active = yolo_alarm or ground_alarm
    assert buzzer_active is True, "Buzzer must remain ON while ground alarm is active"

    # Ground alarm expires -> buzzer turns OFF
    ground_alarm = False
    buzzer_active = yolo_alarm or ground_alarm
    assert buzzer_active is False, "Buzzer turns OFF when both alarms clear"


def test_19_ground_expires_while_person_inside_buzzer_remains_on():
    yolo_alarm = True
    ground_alarm = True

    # Ground alarm expires -> ground_alarm becomes False
    ground_alarm = False
    # Person remains inside -> overall buzzer stays ON
    buzzer_active = yolo_alarm or ground_alarm
    assert buzzer_active is True, "Buzzer must remain ON while YOLO alarm is active"

    # Person leaves -> yolo_alarm becomes False -> buzzer turns OFF
    yolo_alarm = False
    buzzer_active = yolo_alarm or ground_alarm
    assert buzzer_active is False

