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


from pydantic import BaseModel
import base64

class FrameUploadRequest(BaseModel):
    image: str
    camera_id: str = "cam_01"


@router.post("/camera/frame")
async def upload_camera_frame(payload: FrameUploadRequest):
    """Receive JPEG base64 frame from browser webcam and process via YOLO engine."""
    from backend.app import camera_1, camera_2
    target_cam = camera_2 if payload.camera_id in ("cam_02", "cam-02") else camera_1
    img_str = payload.image
    if "," in img_str:
        img_str = img_str.split(",", 1)[1]
    try:
        jpeg_bytes = base64.b64decode(img_str)
        success = target_cam.update_frame(jpeg_bytes)
        if success:
            return {"status": "ok", "fps": round(target_cam.status.fps, 1)}
        else:
            return {"status": "error", "message": "Failed to decode frame"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

