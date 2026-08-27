"""BorderPulse — Devices API"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/devices")
async def list_devices():
    from backend.app import db, esp32_client
    devices = []

    # ESP32
    devices.append({
        "name": "ESP32 Controller",
        "device_type": "esp32",
        "status": "online" if esp32_client.status.online else "offline",
        "ip_address": esp32_client.status.ip,
        "firmware_version": esp32_client.status.firmware_version,
        "last_seen": esp32_client.status.last_seen,
        "error": esp32_client.status.error,
    })

    # Also fetch from Supabase
    if db:
        try:
            result = db.table("devices").select("*").execute()
            if result.data:
                return {"devices": result.data, "esp32_live": devices[0]}
        except Exception:
            pass

    return {"devices": devices}


@router.get("/cameras")
async def list_cameras():
    from backend.app import camera, db
    cam_info = {
        "name": "Laptop Built-in Camera",
        "source_type": "laptop",
        "camera_code": "laptop-cam-0",
        "status": "online" if camera.status.online else "offline",
        "resolution": camera.status.resolution,
        "fps": round(camera.status.fps, 1),
        "error": camera.status.error,
    }
    if db:
        try:
            result = db.table("cameras").select("*").execute()
            return {"cameras": result.data or [], "live_status": cam_info}
        except Exception:
            pass
    return {"cameras": [cam_info]}
