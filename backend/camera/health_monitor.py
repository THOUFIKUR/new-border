"""
BorderPulse — Camera Health Monitor
Analyses frames for brightness, blur, and visibility issues.
Does NOT claim rain/fog detection. Uses measurable image quality metrics.
"""
import cv2
import numpy as np
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CameraHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DARK = "DARK"
    BLURRED = "BLURRED"
    BLOCKED = "BLOCKED"
    LOW_VISIBILITY = "LOW_VISIBILITY"
    OFFLINE = "OFFLINE"


@dataclass
class HealthMetrics:
    state: CameraHealthState = CameraHealthState.OFFLINE
    brightness_score: float = 0.0  # 0–255 mean
    blur_score: float = 0.0        # Laplacian variance; higher = sharper
    visibility_score: float = 0.0  # RMS contrast, 0–1
    fps: float = 0.0
    message: str = ""
    checked_at: float = 0.0


class CameraHealthMonitor:
    """
    Analyses frames periodically and classifies camera health state.
    Called from the inference pipeline — does NOT run in its own thread.
    """

    # Configurable thresholds
    BRIGHTNESS_DARK = 25.0      # Mean pixel < 25 → DARK
    BRIGHTNESS_OVEREXPOSED = 240.0
    BLUR_THRESHOLD = 100.0      # Laplacian variance < 100 → BLURRED
    BLOCKED_BRIGHTNESS = 5.0    # Near-black → likely BLOCKED
    VISIBILITY_LOW = 0.05       # Very low RMS contrast → LOW_VISIBILITY

    def __init__(self):
        self._last_metrics = HealthMetrics()
        self._last_check: float = 0.0
        self._check_interval: float = 2.0  # seconds

    def analyse(self, frame: np.ndarray, fps: float) -> HealthMetrics:
        now = time.monotonic()
        if now - self._last_check < self._check_interval:
            self._last_metrics.fps = fps
            return self._last_metrics

        self._last_check = now
        metrics = HealthMetrics(fps=fps, checked_at=now)

        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Brightness
        brightness = float(np.mean(gray))
        metrics.brightness_score = brightness

        # 2. Blur (Laplacian variance)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        metrics.blur_score = lap_var

        # 3. Visibility (RMS contrast)
        rms = float(np.std(gray)) / 128.0
        metrics.visibility_score = min(1.0, rms)

        # 4. Classify
        if brightness < self.BLOCKED_BRIGHTNESS:
            metrics.state = CameraHealthState.BLOCKED
            metrics.message = "Camera may be physically blocked or lens covered"
        elif brightness < self.BRIGHTNESS_DARK:
            metrics.state = CameraHealthState.DARK
            metrics.message = f"Scene too dark (brightness={brightness:.1f})"
        elif lap_var < self.BLUR_THRESHOLD:
            metrics.state = CameraHealthState.BLURRED
            metrics.message = f"Image blurred (sharpness={lap_var:.1f})"
        elif metrics.visibility_score < self.VISIBILITY_LOW:
            metrics.state = CameraHealthState.LOW_VISIBILITY
            metrics.message = "Very low scene contrast — fog/haze possible (EXPERIMENTAL)"
        elif brightness > self.BRIGHTNESS_OVEREXPOSED:
            metrics.state = CameraHealthState.WARNING
            metrics.message = "Scene may be overexposed"
        else:
            metrics.state = CameraHealthState.HEALTHY
            metrics.message = "Camera healthy"

        self._last_metrics = metrics
        return metrics

    def get_last(self) -> HealthMetrics:
        return self._last_metrics

    def to_dict(self) -> dict:
        m = self._last_metrics
        return {
            "state": m.state.value,
            "brightness_score": round(m.brightness_score, 2),
            "blur_score": round(m.blur_score, 2),
            "visibility_score": round(m.visibility_score, 3),
            "fps": round(m.fps, 1),
            "message": m.message,
        }
