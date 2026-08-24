"""
BorderPulse — Central Configuration
Loads all environment variables and provides typed config to all modules.
Service-role key stays here — backend only.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from workspace root (one level above backend/)
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def _bool(key: str, default: bool) -> bool:
    v = os.getenv(key, str(default)).lower()
    return v in ("1", "true", "yes", "on")


# ─── Supabase ──────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# ─── ESP32 ─────────────────────────────────────────────────────────────────
ESP32_IP: str = os.getenv("ESP32_IP", "192.168.1.100")
ESP32_PORT: int = _int("ESP32_PORT", 80)
ESP32_TIMEOUT: float = _float("ESP32_TIMEOUT_SECONDS", 2.0)
ESP32_HEARTBEAT_INTERVAL: float = _float("ESP32_HEARTBEAT_INTERVAL", 5.0)
ESP32_RETRY_COUNT: int = _int("ESP32_RETRY_COUNT", 2)
ESP32_RETRY_DELAY: float = _float("ESP32_RETRY_DELAY", 1.0)

# Safe startup log — resolved ESP32 target (no secrets). Printed at import time
# so a stale/mismatched IP is visible the moment the backend starts, instead
# of silently causing heartbeat failures that only show up as "ESP32 OFFLINE".
print(f"ESP32 CONFIG: {ESP32_IP}:{ESP32_PORT} (timeout={ESP32_TIMEOUT}s, heartbeat={ESP32_HEARTBEAT_INTERVAL}s)")

# ─── Camera ────────────────────────────────────────────────────────────────
CAMERA_INDEX: int = _int("CAMERA_INDEX", 0)

# ─── YOLO ──────────────────────────────────────────────────────────────────
YOLO_MODEL: str = os.getenv("YOLO_MODEL", "models/yolo/yolo11n.pt")
YOLO_CONFIDENCE: float = _float("YOLO_CONFIDENCE", 0.50)
YOLO_HUMAN_HIGH_CONFIDENCE: float = _float("YOLO_HUMAN_HIGH_CONFIDENCE", 0.85)
YOLO_IMGSZ: int = _int("YOLO_IMGSZ", 640)
YOLO_IOU: float = _float("YOLO_IOU", 0.45)

# Classes of interest (COCO subset relevant to intrusion)
YOLO_CLASSES_OF_INTEREST = [
    "person", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe",
    "car", "motorcycle", "bus", "truck", "bicycle",
]

# ─── Runtime ───────────────────────────────────────────────────────────────
RUNTIME_MODE: str = os.getenv("RUNTIME_MODE", "laptop")
SENSOR_SIMULATION: bool = _bool("SENSOR_SIMULATION", True)

# ─── Evidence ──────────────────────────────────────────────────────────────
PRE_EVENT_SECONDS: float = _float("PRE_EVENT_SECONDS", 5.0)
POST_EVENT_SECONDS: float = _float("POST_EVENT_SECONDS", 8.0)
MAX_CLIP_SECONDS: float = _float("MAX_CLIP_SECONDS", 30.0)
EVIDENCE_LOCAL_DIR: Path = _ROOT / os.getenv("EVIDENCE_LOCAL_DIR", "evidence_local")

# ─── Decision engine ───────────────────────────────────────────────────────
EVENT_COOLDOWN_SECONDS: float = _float("EVENT_COOLDOWN_SECONDS", 10.0)
TEMPORAL_MIN_FRAMES: int = _int("TEMPORAL_MIN_FRAMES", 3)
TEMPORAL_WINDOW_SECONDS: float = _float("TEMPORAL_WINDOW_SECONDS", 1.0)

# ─── Sensor fusion weights ─────────────────────────────────────────────────
FUSION_WEIGHT_VISION: float = _float("FUSION_WEIGHT_VISION", 0.55)
FUSION_WEIGHT_RADAR: float = _float("FUSION_WEIGHT_RADAR", 0.20)
FUSION_WEIGHT_GROUND: float = _float("FUSION_WEIGHT_GROUND", 0.15)
FUSION_WEIGHT_TEMPORAL: float = _float("FUSION_WEIGHT_TEMPORAL", 0.10)
FUSION_CONFIRMED_THRESHOLD: float = _float("FUSION_CONFIRMED_THRESHOLD", 0.65)

# ─── Streaming ─────────────────────────────────────────────────────────────
STREAM_FPS: int = _int("STREAM_FPS", 15)
STREAM_JPEG_QUALITY: int = _int("STREAM_JPEG_QUALITY", 75)
BACKEND_PORT: int = _int("BACKEND_PORT", 8000)
BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")

# ─── Storage buckets ───────────────────────────────────────────────────────
BUCKET_IMAGES: str = "event-images"
BUCKET_VIDEOS: str = "event-videos"
