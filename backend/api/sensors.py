"""BorderPulse — Sensors API"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SimulationControl(BaseModel):
    radar: bool = False
    ground: bool = False


@router.get("/sensors/state")
async def get_sensor_state():
    from backend.app import sensor_provider, esp32_client
    state = sensor_provider.get_state()
    esp32_sensors = None
    if esp32_client.status.online:
        esp32_sensors = esp32_client.get_sensors()
    return {
        "sensors": state.to_dict(),
        "esp32_sensors": esp32_sensors,
        "note": "Radar and ground sensors are SIMULATED — not real hardware readings",
    }


@router.post("/sensors/simulate")
async def set_simulation(body: SimulationControl):
    from backend.app import sensor_provider
    sensor_provider.set_simulation(radar=body.radar, ground=body.ground)
    state = sensor_provider.get_state()
    return {
        "success": True,
        "simulation": {"radar": body.radar, "ground": body.ground},
        "state": state.to_dict(),
        "warning": "These are SIMULATED sensor values — not real hardware readings",
    }


@router.post("/sensors/simulate/radar")
async def toggle_radar(body: dict):
    from backend.app import sensor_provider
    value = bool(body.get("active", False))
    sensor_provider.set_radar(value)
    return {"success": True, "radar_simulated": value}


@router.post("/sensors/simulate/ground")
async def toggle_ground(body: dict):
    from backend.app import sensor_provider
    value = bool(body.get("active", False))
    sensor_provider.set_ground(value)
    return {"success": True, "ground_simulated": value}
