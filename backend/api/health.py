"""BorderPulse — Health API"""
from fastapi import APIRouter
from backend.database.supabase_client import check_supabase_connection
import backend.config as cfg

router = APIRouter()


@router.get("/health")
async def health():
    from backend.app import camera, detector, esp32_client, sensor_provider
    sensor_state = sensor_provider.get_state()
    supabase_ok = False
    try:
        supabase_ok = check_supabase_connection()
    except Exception:
        pass

    return {
        "status": "running",
        "camera": {
            "online": camera.status.online,
            "fps": round(camera.status.fps, 1),
            "resolution": camera.status.resolution,
            "error": camera.status.error,
            "label": "CAMERA ✓" if camera.status.online else "CAMERA ✗",
        },
        "yolo": {
            "ready": detector.ready,
            "model": cfg.YOLO_MODEL,
            "error": detector.error,
            "label": "YOLO ✓" if detector.ready else f"YOLO ✗ {detector.error}",
        },
        "supabase": {
            "connected": supabase_ok,
            "url": cfg.SUPABASE_URL,
            "label": "SUPABASE ✓" if supabase_ok else "SUPABASE ✗",
        },
        "esp32": esp32_client.status.to_dict(),
        "radar": {
            "mode": sensor_state.radar_mode.value,
            "label": f"RADAR — {sensor_state.radar_mode.value}",
        },
        "ground": {
            "mode": sensor_state.ground_mode.value,
            "label": f"GROUND — {sensor_state.ground_mode.value}",
        },
        "runtime_mode": cfg.RUNTIME_MODE,
        "sensor_simulation": cfg.SENSOR_SIMULATION,
    }
