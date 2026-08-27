"""
BorderPulse — Sensor Fusion Engine
Computes a fused evidence score from vision, radar, ground, and temporal confirmation.
Weights are configurable. These are engineering starting values, NOT validated constants.

IMPORTANT engineering constraints:
- Radar provides MOTION EVIDENCE, not human identity.
- Ground sensor provides PHYSICAL DISTURBANCE evidence, not human classification.
- Only vision can classify what class an object is.
"""
import time
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("borderpulse.fusion")


@dataclass
class FusionInput:
    vision_confidence: float        # 0.0–1.0 from YOLO
    radar_triggered: bool           # True = motion detected (SIMULATED or REAL)
    ground_triggered: bool          # True = vibration detected (SIMULATED or REAL)
    temporal_confirmed: bool        # True = >= min_frames in window
    class_name: str = "person"
    track_id: Optional[int] = None
    inside_zone: bool = False


@dataclass
class FusionResult:
    fused_score: float              # 0.0–1.0
    is_confirmed: bool              # Above confirmed threshold
    evidence: dict                  # What contributed
    decision_label: str             # Human-readable
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class FusionEngine:
    """
    Weighted evidence fusion.
    Configurable weights sum should approximate 1.0.
    """

    def __init__(
        self,
        w_vision: float = 0.55,
        w_radar: float = 0.20,
        w_ground: float = 0.15,
        w_temporal: float = 0.10,
        confirmed_threshold: float = 0.65,
    ):
        self.w_vision = w_vision
        self.w_radar = w_radar
        self.w_ground = w_ground
        self.w_temporal = w_temporal
        self.confirmed_threshold = confirmed_threshold

    def update_weights(self, w_vision: float, w_radar: float,
                       w_ground: float, w_temporal: float,
                       confirmed_threshold: float):
        self.w_vision = w_vision
        self.w_radar = w_radar
        self.w_ground = w_ground
        self.w_temporal = w_temporal
        self.confirmed_threshold = confirmed_threshold
        logger.info(f"Fusion weights updated: V={w_vision} R={w_radar} G={w_ground} T={w_temporal} thr={confirmed_threshold}")

    def compute(self, inp: FusionInput) -> FusionResult:
        # Vision contribution
        v_score = inp.vision_confidence * self.w_vision

        # Radar: motion evidence only — boolean trigger
        r_score = self.w_radar if inp.radar_triggered else 0.0

        # Ground: physical disturbance evidence only — boolean trigger
        g_score = self.w_ground if inp.ground_triggered else 0.0

        # Temporal: consecutive frames confirmed
        t_score = self.w_temporal if inp.temporal_confirmed else 0.0

        fused = min(1.0, v_score + r_score + g_score + t_score)
        is_confirmed = fused >= self.confirmed_threshold

        evidence = {
            "vision_contribution": round(v_score, 3),
            "radar_contribution": round(r_score, 3),
            "ground_contribution": round(g_score, 3),
            "temporal_contribution": round(t_score, 3),
            "radar_note": "MOTION EVIDENCE (not human identity)",
            "ground_note": "PHYSICAL DISTURBANCE (not human identity)",
        }

        # Determine label
        if inp.class_name == "person" and inp.inside_zone:
            if inp.vision_confidence >= 0.85:
                label = "CRITICAL HUMAN INTRUSION"
            elif is_confirmed:
                label = "CONFIRMED INTRUSION"
            elif inp.radar_triggered or inp.ground_triggered:
                label = "PROBABLE INTRUSION"
            else:
                label = "POSSIBLE DETECTION"
        elif inp.radar_triggered and not inp.inside_zone:
            label = "MOTION WARNING"
        elif inp.ground_triggered and not inp.inside_zone:
            label = "GROUND DISTURBANCE"
        elif is_confirmed:
            label = f"CONFIRMED: {inp.class_name.upper()}"
        else:
            label = f"POSSIBLE: {inp.class_name.upper()}"

        return FusionResult(
            fused_score=round(fused, 3),
            is_confirmed=is_confirmed,
            evidence=evidence,
            decision_label=label,
        )
