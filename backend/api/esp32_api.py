"""BorderPulse — ESP32 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class AlarmCommand(BaseModel):
    active: bool
    reason: str = "test"
    duration_ms: int = 3000


@router.get("/esp32/status")
async def esp32_status():
    from backend.app import esp32_client
    return esp32_client.status.to_dict()


@router.post("/esp32/alarm")
async def trigger_alarm(body: AlarmCommand):
    from backend.app import esp32_client
    if not body.active:
        ok = esp32_client.stop_alarm()
        return {"success": ok, "action": "alarm_stopped"}
    ok = esp32_client.trigger_alarm(reason=body.reason, duration_ms=body.duration_ms)
    if not ok and not esp32_client.status.online:
        return {"success": False, "error": "ESP32 OFFLINE — alarm not sent", "esp32_status": "OFFLINE"}
    return {"success": ok, "action": "alarm_triggered", "reason": body.reason}


@router.post("/esp32/alarm/stop")
async def stop_alarm():
    from backend.app import esp32_client
    ok = esp32_client.stop_alarm()
    return {"success": ok}


@router.post("/esp32/test/buzzer")
async def test_buzzer():
    from backend.app import esp32_client
    if not esp32_client.status.online:
        return {"success": False, "error": "ESP32 OFFLINE", "note": "Connect ESP32 to test buzzer"}
    ok = esp32_client.test_buzzer()
    return {"success": ok}


@router.get("/esp32/sensors")
async def esp32_sensors():
    from backend.app import esp32_client
    if not esp32_client.status.online:
        return {"online": False, "sensors": None}
    data = esp32_client.get_sensors()
    return {"online": True, "sensors": data}
