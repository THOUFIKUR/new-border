"""
BorderPulse — Sensor Provider Abstract Interface + Simulated Implementation
The decision engine depends on SensorProvider, NOT on specific hardware.
This allows future Raspberry Pi migration without changing the decision engine.
"""
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("borderpulse.sensors")


class SensorMode(str, Enum):
    REAL = "REAL"
    SIMULATED = "SIMULATED"
    OFFLINE = "OFFLINE"


@dataclass
class SensorState:
    radar_triggered: bool = False
    ground_triggered: bool = False
    radar_mode: SensorMode = SensorMode.SIMULATED
    ground_mode: SensorMode = SensorMode.SIMULATED
    last_radar_time: Optional[float] = None
    last_ground_time: Optional[float] = None
    radar_health: str = "ok"
    ground_health: str = "ok"

    def to_dict(self) -> dict:
        return {
            "radar": {
                "triggered": self.radar_triggered,
                "mode": self.radar_mode.value,
                "last_trigger": self.last_radar_time,
                "health": self.radar_health,
                "label": "RADAR — SIMULATED" if self.radar_mode == SensorMode.SIMULATED else
                         "RADAR — REAL HARDWARE" if self.radar_mode == SensorMode.REAL else
                         "RADAR — OFFLINE",
            },
            "ground": {
                "triggered": self.ground_triggered,
                "mode": self.ground_mode.value,
                "last_trigger": self.last_ground_time,
                "health": self.ground_health,
                "label": "GROUND — SIMULATED" if self.ground_mode == SensorMode.SIMULATED else
                         "GROUND — REAL HARDWARE" if self.ground_mode == SensorMode.REAL else
                         "GROUND — OFFLINE",
            },
        }


class SensorProvider(ABC):
    """Abstract sensor interface. Decision engine only depends on this."""

    @abstractmethod
    def get_state(self) -> SensorState:
        """Return current sensor state."""
        ...

    @abstractmethod
    def set_simulation(self, radar: bool, ground: bool):
        """Override simulated sensor values."""
        ...


class SimulatedSensorProvider(SensorProvider):
    """
    Simulated radar and ground sensor.
    Values are set manually via the API for testing/demo.
    Clearly marked SIMULATED — never presented as real hardware readings.
    """

    def __init__(self):
        self._radar_sim = False
        self._ground_sim = False

    def get_state(self) -> SensorState:
        return SensorState(
            radar_triggered=self._radar_sim,
            ground_triggered=self._ground_sim,
            radar_mode=SensorMode.SIMULATED,
            ground_mode=SensorMode.SIMULATED,
            last_radar_time=time.time() if self._radar_sim else None,
            last_ground_time=time.time() if self._ground_sim else None,
        )

    def set_simulation(self, radar: bool, ground: bool):
        prev_radar = self._radar_sim
        prev_ground = self._ground_sim
        self._radar_sim = radar
        self._ground_sim = ground
        if radar != prev_radar or ground != prev_ground:
            logger.info(f"[SIMULATED] Radar={radar} Ground={ground}")

    def set_radar(self, value: bool):
        self._radar_sim = value

    def set_ground(self, value: bool):
        self._ground_sim = value
