"""
BorderPulse — Main FastAPI Application
Orchestrates: camera → YOLO → zones → decision → events → streaming → ESP32 → Supabase

Startup order:
1. Load config
2. Initialize Supabase client
3. Start camera capture thread
4. Load YOLO model
5. Start YOLO inference thread
6. Load zones from Supabase
7. Start ESP32 heartbeat
8. Start WebSocket streaming
9. Report health status
"""
import asyncio
import base64
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import backend.config as cfg
from backend.camera.capture import CameraCapture
from backend.camera.health_monitor import CameraHealthMonitor
from backend.vision.detector import YOLODetector, DETECTION_QUEUE, Detection
from backend.vision.zones import ZoneEngine
from backend.vision.annotator import annotate_frame
from backend.decision.engine import DecisionEngine
from backend.decision.fusion import FusionEngine, FusionInput
from backend.sensors.provider import SimulatedSensorProvider
from backend.events.manager import EventManager
from backend.evidence.capture import EvidenceCapture
from backend.hardware.esp32 import ESP32Client
from backend.database.supabase_client import get_service_client, check_supabase_connection

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("borderpulse.app")

# ── Global singletons (initialized in lifespan) ───────────────────────────
camera = CameraCapture(cfg.CAMERA_INDEX)
health_monitor = CameraHealthMonitor()
detector = YOLODetector(
    model_path=cfg.YOLO_MODEL,
    confidence=cfg.YOLO_CONFIDENCE,
    imgsz=cfg.YOLO_IMGSZ,
    iou=cfg.YOLO_IOU,
)
zone_engine = ZoneEngine()
fusion_engine = FusionEngine(
    w_vision=cfg.FUSION_WEIGHT_VISION,
    w_radar=cfg.FUSION_WEIGHT_RADAR,
    w_ground=cfg.FUSION_WEIGHT_GROUND,
    w_temporal=cfg.FUSION_WEIGHT_TEMPORAL,
    confirmed_threshold=cfg.FUSION_CONFIRMED_THRESHOLD,
)
decision_engine = DecisionEngine(
    min_frames=cfg.TEMPORAL_MIN_FRAMES,
    window_seconds=cfg.TEMPORAL_WINDOW_SECONDS,
    cooldown_seconds=cfg.EVENT_COOLDOWN_SECONDS,
    human_high_confidence=cfg.YOLO_HUMAN_HIGH_CONFIDENCE,
    person_confirmation_frames=cfg.PERSON_CONFIRMATION_FRAMES,
    bbox_max_center_jump=cfg.BBOX_STABILITY_MAX_CENTER_JUMP,
    bbox_max_size_ratio=cfg.BBOX_STABILITY_MAX_SIZE_RATIO,
)
sensor_provider = SimulatedSensorProvider()
esp32_client = ESP32Client()
evidence_capture = EvidenceCapture(
    local_dir=cfg.EVIDENCE_LOCAL_DIR,
    pre_event_seconds=cfg.PRE_EVENT_SECONDS,
    post_event_seconds=cfg.POST_EVENT_SECONDS,
    target_fps=cfg.STREAM_FPS,
)
event_manager = EventManager()

db = None  # Supabase service client

# ── Shared state ──────────────────────────────────────────────────────────
_latest_stream_data: dict = {}
_active_ws_clients: List[WebSocket] = []
_health_status: dict = {}
_last_buzzer_pulse: float = 0.0
_buzzer_active_state: bool = False
_last_ground_trigger_time: float = 0.0

# ── Startup/Shutdown ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db

    logger.info("=" * 60)
    logger.info("BorderPulse — Starting up")
    logger.info("=" * 60)

    health = {"camera": False, "yolo": False, "supabase": False,
               "esp32": False, "storage": False, "radar": "SIMULATED", "ground": "SIMULATED"}

    # 1. Supabase
    logger.info("Connecting to Supabase...")
    db = get_service_client()
    supabase_ok = check_supabase_connection()
    health["supabase"] = supabase_ok
    if supabase_ok:
        logger.info("SUPABASE ✓")
        event_manager._db = db
        # Register/update this laptop camera in Supabase
        await _register_camera()
        # Load zones
        await _load_zones_from_db()
    else:
        logger.warning("SUPABASE ✗ — continuing without database")

    # 2. Camera
    logger.info("Starting camera...")
    cam_ok = camera.start()
    health["camera"] = cam_ok
    if cam_ok:
        logger.info(f"CAMERA ✓ — {camera.status.resolution}")
        time.sleep(0.5)  # Warm up
    else:
        logger.error(f"CAMERA ✗ — {camera.status.error}")

    # 3. YOLO
    logger.info("Loading YOLO model...")
    yolo_ok = detector.load()
    health["yolo"] = yolo_ok
    if yolo_ok:
        logger.info("YOLO ✓")
        if cam_ok:
            detector.start(camera)
    else:
        logger.error(f"YOLO ✗ — {detector.error}")

    # 4. ESP32
    logger.info("Starting ESP32 client...")
    esp32_client.start()
    # Wait long enough for first heartbeat to complete (heartbeat_interval = 5s)
    logger.info("Waiting for ESP32 heartbeat...")
    await asyncio.sleep(cfg.ESP32_HEARTBEAT_INTERVAL + 1.0)
    health["esp32"] = esp32_client.status.online
    if esp32_client.status.online:
        logger.info(f"ESP32 ✓ — IP={cfg.ESP32_IP} firmware={esp32_client.status.firmware_version}")
    else:
        logger.warning(f"ESP32 OFFLINE — IP={cfg.ESP32_IP} error={esp32_client.status.error}")
        logger.warning("Vision continues without hardware alerts. Check ESP32_IP in .env")

    _health_status.update(health)

    logger.info("=" * 60)
    logger.info(f"CAMERA    {'✓' if health['camera'] else '✗'}")
    logger.info(f"YOLO      {'✓' if health['yolo'] else '✗'}")
    logger.info(f"SUPABASE  {'✓' if health['supabase'] else '✗'}")
    logger.info(f"ESP32     {'✓' if health['esp32'] else 'OFFLINE'}")
    logger.info(f"RADAR     {health['radar']}")
    logger.info(f"GROUND    {health['ground']}")
    logger.info("=" * 60)

    # Start main processing loop
    asyncio.create_task(_processing_loop())

    yield

    # Shutdown
    logger.info("BorderPulse shutting down...")
    camera.stop()
    detector.stop()
    esp32_client.stop()


async def _register_camera():
    """Register this laptop camera in Supabase cameras table."""
    if not db:
        return
    try:
        result = db.table("cameras").select("id").eq("camera_code", "laptop-cam-0").execute()
        if not result.data:
            db.table("cameras").insert({
                "camera_code": "laptop-cam-0",
                "name": "Laptop Built-in Camera",
                "source_type": "laptop",
                "source_uri": f"index:{cfg.CAMERA_INDEX}",
                "status": "online",
            }).execute()
            logger.info("Camera registered in Supabase")
        else:
            db.table("cameras").update({"status": "online"}).eq("camera_code", "laptop-cam-0").execute()
        # Get camera ID
        result = db.table("cameras").select("id").eq("camera_code", "laptop-cam-0").execute()
        if result.data:
            camera_id = result.data[0]["id"]
            event_manager.set_camera_id(camera_id)
    except Exception as e:
        logger.error(f"Camera registration failed: {e}")


async def _load_zones_from_db():
    """Load existing zones from Supabase."""
    if not db:
        return
    try:
        result = db.table("zones").select("*").execute()
        if result.data:
            zone_engine.load_zones(result.data)
    except Exception as e:
        logger.error(f"Zone loading failed: {e}")


# ── Main Processing Loop ──────────────────────────────────────────────────

async def _processing_loop():
    """
    Main async loop that:
    1. Gets latest detection from YOLO queue
    2. Runs zone engine
    3. Runs fusion engine
    4. Runs decision engine
    5. Triggers events/ESP32/evidence
    6. Broadcasts to WebSocket clients
    """
    import queue as _q
    global _latest_stream_data

    frame_interval = 1.0 / cfg.STREAM_FPS
    last_frame_time = 0.0
    current_decision_label = ""
    current_detections = []

    while True:
        now = asyncio.get_event_loop().time()

        # Throttle WebSocket broadcast to STREAM_FPS
        if now - last_frame_time < frame_interval:
            await asyncio.sleep(0.005)
            continue

        last_frame_time = now

        # Get latest detection result (non-blocking)
        det_frame = None
        try:
            det_frame = DETECTION_QUEUE.get_nowait()
        except _q.Empty:
            pass

        # Get current frame for streaming
        frame_jpeg = camera.get_latest_jpeg()
        raw_frame = camera.get_latest_raw()

        # Update pre-event buffer
        if raw_frame is not None:
            evidence_capture.push_frame(raw_frame)

        # Process detections
        if det_frame:
            current_detections = det_frame.detections
            # Get sensor state & check real ESP32 ground sensor
            sensor_state = sensor_provider.get_state()
            ground_active = sensor_state.ground_triggered
            if esp32_client.status.online:
                esp_sens = esp32_client.get_sensors()
                if esp_sens and "ground" in esp_sens and "triggered" in esp_sens["ground"]:
                    ground_active = bool(esp_sens["ground"]["triggered"])

            new_label = current_decision_label

            # Per-detection processing
            for det in det_frame.detections:
                if not det.bbox_norm:
                    continue

                # Zone check
                triggered_zones = zone_engine.check_detection(det.class_name, det.bbox_norm)
                inside_zone = len(triggered_zones) > 0
                zone_id = triggered_zones[0] if triggered_zones else "no-zone"

                if not inside_zone and det.class_name == "person":
                    # Still check any zone for person if class filter differs
                    any_triggered = zone_engine.check_any_zone(det.bbox_norm)
                    inside_zone = len(any_triggered) > 0
                    zone_id = any_triggered[0] if any_triggered else "no-zone"

                if not inside_zone:
                    continue  # Not in any zone — skip decision engine

                # Fusion
                fusion_in = FusionInput(
                    vision_confidence=det.confidence,
                    radar_triggered=sensor_state.radar_triggered,
                    ground_triggered=ground_active,
                    temporal_confirmed=False,  # Will be set by decision engine output
                    class_name=det.class_name,
                    track_id=det.track_id,
                    inside_zone=True,
                )
                fusion_out = fusion_engine.compute(fusion_in)

                # Decision — pass bbox_norm for stability check
                logger.debug(
                    f"[ZONE] track={det.track_id} class={det.class_name} INSIDE zone={zone_id}"
                )
                decision_out = decision_engine.process(
                    track_id=det.track_id,
                    zone_id=zone_id,
                    class_name=det.class_name,
                    confidence=det.confidence,
                    fused_score=fusion_out.fused_score,
                    is_confirmed_fused=fusion_out.is_confirmed,
                    decision_label=fusion_out.decision_label,
                    bbox_norm=det.bbox_norm,
                )

                if decision_out.should_alarm or decision_out.is_critical:
                    new_label = fusion_out.decision_label

                    # Build human-readable trigger source label
                    trigger_sources = ["YOLO-VISION"]
                    if sensor_state.radar_triggered:
                        trigger_sources.append("RADAR-SIM")
                    if ground_active:
                        trigger_sources.append("GROUND-SENSOR")
                    trigger_label = " + ".join(trigger_sources)
                    event_reason = f"{fusion_out.decision_label} [{trigger_label}]"

                    logger.info(f"[FUSION] score={fusion_out.fused_score:.3f} label={fusion_out.decision_label}")
                    logger.info(f"[EVENT] CREATING track={det.track_id} zone={zone_id} reason={event_reason}")

                    # Create event
                    if decision_out.should_create_event:
                        event = event_manager.create_event(
                            track_id=det.track_id,
                            zone_id=zone_id,
                            class_name=det.class_name,
                            confidence=det.confidence,
                            fused_score=fusion_out.fused_score,
                            is_critical=decision_out.is_critical,
                            reason=event_reason,
                            sensor_evidence={
                                **fusion_out.evidence,
                                "trigger_source": trigger_label,
                                "ground_active": ground_active,
                                "radar_active": sensor_state.radar_triggered,
                                "person_confirm_count": decision_out.person_confirm_count,
                                "person_confirm_required": decision_out.person_confirm_required,
                            },
                        )
                        logger.info(f"[EVENT] CREATED id={event.id if event else 'COOLDOWN'}")
                        # Trigger ESP32 buzzer (non-blocking) — only for persons
                        if det.class_name == "person" and event:
                            logger.info(
                                f"[ESP32_REQUEST] ALARM active=true reason={event_reason} "
                                f"esp32_online={esp32_client.status.online} "
                                f"track={det.track_id} conf={det.confidence:.2f}"
                            )
                            loop = asyncio.get_running_loop()
                            future = loop.run_in_executor(
                                None, esp32_client.trigger_alarm, event_reason
                            )
                            # Fire-and-forget but log the result
                            def _log_esp32_result(fut, reason=event_reason):
                                try:
                                    ok = fut.result()
                                    if ok:
                                        logger.info(f"[ESP32_RESPONSE] 200 OK — reason={reason}")
                                        logger.info(f"[BUZZER] ACTIVE")
                                    else:
                                        logger.warning(f"[ESP32_RESPONSE] FAILED — ESP32 offline or error")
                                        logger.warning(f"[BUZZER] NOT ACTIVATED — hardware unavailable")
                                except Exception as exc:
                                    logger.error(f"[ESP32_RESPONSE] exception: {exc}")
                            future.add_done_callback(_log_esp32_result)
                            # Start evidence capture
                            if decision_out.should_capture and raw_frame is not None:
                                evidence_capture.trigger(
                                    event_id=event.id,
                                    snapshot_callback=_evidence_ready_callback,
                                )

            current_decision_label = new_label

        # ── Continuous ESP32 Buzzer Sustain Control ──────────────────────────────────
        # The decision engine fires the alarm when a person is CONFIRMED (4 frames).
        # This loop sustains the buzzer while a confirmed alarm is still active,
        # and turns it off when no more confirmed tracks are in ALARM_ACTIVE state.
        # It does NOT bypass the decision engine — it only sustains an already-fired alarm.
        global _last_buzzer_pulse, _buzzer_active_state, _last_ground_trigger_time

        now_mono = time.monotonic()

        # Sustain: any track in ALARM_ACTIVE state
        any_alarm_active = any(
            s["state"] in ("ALARM_ACTIVE", "EVIDENCE_CAPTURE", "EVENT_ACTIVE")
            for s in decision_engine.get_all_states()
        )

        # Update real ground sensor trigger hold time
        if ground_active:
            _last_ground_trigger_time = now_mono

        ground_hold_active = (now_mono - _last_ground_trigger_time) < 2.0

        # Buzzer active if: decision engine confirmed alarm OR ground sensor active
        alarm_needed = any_alarm_active or ground_hold_active

        if alarm_needed:
            if not _buzzer_active_state or (now_mono - _last_buzzer_pulse >= 2.0):
                _last_buzzer_pulse = now_mono
                _buzzer_active_state = True
                if esp32_client.status.online:
                    reason = "GROUND_SENSOR_ACTIVE" if ground_hold_active and not any_alarm_active else "VISION_CONFIRMED_INTRUSION"
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, esp32_client.trigger_alarm, reason, 2500)
        else:
            if _buzzer_active_state:
                _buzzer_active_state = False
                if esp32_client.status.online:
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, esp32_client.stop_alarm)

        if raw_frame is not None:
            try:
                annotated_jpeg = annotate_frame(
                    raw_frame,
                    current_detections,
                    zone_engine.get_zones(),
                    current_decision_label,
                    cfg.STREAM_JPEG_QUALITY,
                )
                frame_b64 = base64.b64encode(annotated_jpeg).decode()
            except Exception as e:
                logger.debug(f"Frame annotation error: {e}")
                frame_b64 = ""
        else:
            frame_b64 = ""

        # Build stream payload with real sensor status
        sensor_state_dict = {
            "radar": {
                "triggered": False,
                "mode": "OFFLINE",
                "last_trigger": None,
                "health": "ok",
                "label": "RADAR — NOT CONNECTED",
            },
            "ground": {
                "triggered": ground_active,
                "mode": "REAL" if esp32_client.status.online else "SIMULATED",
                "last_trigger": _last_ground_trigger_time if _last_ground_trigger_time > 0 else None,
                "health": "ok",
                "label": "GROUND — REAL HARDWARE" if esp32_client.status.online else "GROUND — SIMULATED",
            },
        }

        stream_payload = {
            "frame": frame_b64,
            "detections": [d.to_dict() for d in current_detections],
            "zones": zone_engine.to_frontend_list(),
            "decision_state": current_decision_label,
            "sensor_state": sensor_state_dict,
            "temporal_states": decision_engine.get_all_states(),
            "buzzer_active": _buzzer_active_state,
            "camera_status": {
                "online": camera.status.online,
                "fps": round(camera.status.fps, 1),
                "resolution": camera.status.resolution,
                "error": camera.status.error,
            },
            "inference_latency_ms": detector.last_latency_ms,
            "esp32_status": esp32_client.status.to_dict(),
            "active_events": [e.to_dict() for e in event_manager.get_active_events()[:5]],
            "timestamp": time.time(),
        }
        _latest_stream_data = stream_payload

        # Broadcast to connected WebSocket clients
        if _active_ws_clients:
            msg = json.dumps(stream_payload)
            dead = []
            for ws in _active_ws_clients:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                _active_ws_clients.remove(ws)


def _evidence_ready_callback(event_id: str, snapshot_path, video_path):
    """Called when evidence capture is complete — upload to Supabase Storage."""
    if not db:
        logger.warning("Evidence ready but Supabase not available — local only")
        return
    try:
        from backend.evidence.storage import StorageUploader
        from supabase import create_client
        storage_client = create_client(cfg.SUPABASE_URL, cfg.SUPABASE_SERVICE_ROLE_KEY)
        uploader = StorageUploader(storage_client, db)
        if snapshot_path:
            uploader.upload_snapshot(event_id, snapshot_path)
        if video_path:
            uploader.upload_video(event_id, video_path)
    except Exception as e:
        logger.error(f"Evidence upload callback failed: {e}")


# ── FastAPI App ───────────────────────────────────────────────────────────

app = FastAPI(
    title="BorderPulse API",
    description="AI Multi-Sensor Restricted-Area Intrusion Detection",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ───────────────────────────────────────────────────────
from backend.api.health import router as health_router
from backend.api.events import router as events_router
from backend.api.zones import router as zones_router
from backend.api.sensors import router as sensors_router
from backend.api.devices import router as devices_router
from backend.api.esp32_api import router as esp32_router
from backend.api.settings import router as settings_router

app.include_router(health_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(zones_router, prefix="/api")
app.include_router(sensors_router, prefix="/api")
app.include_router(devices_router, prefix="/api")
app.include_router(esp32_router, prefix="/api")
app.include_router(settings_router, prefix="/api")

# ── WebSocket ─────────────────────────────────────────────────────────────

@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await ws.accept()
    _active_ws_clients.append(ws)
    logger.info(f"WebSocket client connected. Total: {len(_active_ws_clients)}")
    try:
        while True:
            # Keep alive — client can send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _active_ws_clients:
            _active_ws_clients.remove(ws)
        logger.info(f"WebSocket client disconnected. Total: {len(_active_ws_clients)}")


# ── Root ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "project": "BorderPulse",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "websocket": "ws://localhost:8000/ws/stream",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=cfg.BACKEND_HOST,
        port=cfg.BACKEND_PORT,
        reload=False,
        log_level="info",
    )
