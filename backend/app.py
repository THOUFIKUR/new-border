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
from backend.vision.zones import ZoneEngine, bottom_center as _bbox_bottom_center
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
camera_1 = CameraCapture(cfg.CAMERA_1_INDEX, camera_name="CAM-01")
camera_2 = CameraCapture(cfg.CAMERA_2_INDEX, camera_name="CAM-02")
camera = camera_1  # Primary alias for backward compatibility
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
_yolo_alarm_active: bool = False
_ground_alarm_active_state: bool = False
_ground_consecutive_yes: int = 0
_ground_alarm_expires_at: float = 0.0
_esp32_buzzer_on: bool = False
_current_alarm_reason: str = ""
_last_ground_logged_state: Optional[bool] = None
_last_ground_trigger_time: float = 0.0
# Per-frame zone membership status for annotator debug overlay.
# Keyed by track_id. Rebuilt each detection frame.
_zone_status: dict = {}

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
        logger.info("SUPABASE [OK]")
        event_manager._db = db
        # Register/update this laptop camera in Supabase
        await _register_camera()
        # Load zones
        await _load_zones_from_db()
    else:
        logger.warning("SUPABASE [FAIL] — continuing without database")

    # 2. Camera Hardware Detection & Startup
    from backend.camera.capture import detect_available_cameras
    detect_available_cameras(max_index=4)

    logger.info("Starting cameras...")
    cam_ok = camera_1.start()
    cam2_ok = camera_2.start()
    health["camera"] = cam_ok
    if cam_ok:
        logger.info(f"[CAMERA] CAM-01 started index={cfg.CAMERA_1_INDEX} resolution={camera_1.status.resolution}")
        time.sleep(0.5)  # Warm up
    else:
        logger.error(f"[CAMERA] CAM-01 index={cfg.CAMERA_1_INDEX} FAILED — {camera_1.status.error}")

    if cam2_ok:
        logger.info(f"[CAMERA] CAM-02 started index={cfg.CAMERA_2_INDEX} resolution={camera_2.status.resolution}")
    else:
        logger.info(f"[CAMERA] CAM-02 index={cfg.CAMERA_2_INDEX} FAILED — {camera_2.status.error}")

    # 3. YOLO
    logger.info("Loading YOLO model...")
    yolo_ok = detector.load()
    health["yolo"] = yolo_ok
    if yolo_ok:
        logger.info("YOLO [OK]")
        if cam_ok:
            detector.start(camera)
    else:
        logger.error(f"YOLO [FAIL] — {detector.error}")

    # 4. ESP32
    logger.info("Starting ESP32 client...")
    esp32_client.start()
    # Wait long enough for first heartbeat to complete (heartbeat_interval = 5s)
    logger.info("Waiting for ESP32 heartbeat...")
    await asyncio.sleep(cfg.ESP32_HEARTBEAT_INTERVAL + 1.0)
    health["esp32"] = esp32_client.status.online
    if esp32_client.status.online:
        logger.info(f"ESP32 [OK] — IP={cfg.ESP32_IP} firmware={esp32_client.status.firmware_version}")
        health["ground"] = "REAL"   # GPIO 26 is real when ESP32 is online (P6 fix)
    else:
        logger.warning(f"ESP32 OFFLINE — IP={cfg.ESP32_IP} error={esp32_client.status.error}")
        logger.warning("Vision continues without hardware alerts. Check ESP32_IP in .env")
        health["ground"] = "SIMULATED"

    _health_status.update(health)

    logger.info("=" * 60)
    logger.info(f"CAMERA    {'[OK]' if health['camera'] else '[FAIL]'}")
    logger.info(f"YOLO      {'[OK]' if health['yolo'] else '[FAIL]'}")
    logger.info(f"SUPABASE  {'[OK]' if health['supabase'] else '[FAIL]'}")
    logger.info(f"ESP32     {'[OK]' if health['esp32'] else 'OFFLINE'}")
    logger.info(f"RADAR     {health['radar']} (NOT PHYSICALLY CONNECTED — prototype simulation)")
    logger.info(f"GROUND    {health['ground']} {'(GPIO 26 via ESP32)' if health['ground'] == 'REAL' else '(ESP32 offline)'}")
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
    global _latest_stream_data, _buzzer_active_state, _yolo_alarm_active, _ground_alarm_active_state
    global _ground_consecutive_yes, _ground_alarm_expires_at, _esp32_buzzer_on, _current_alarm_reason
    global _last_ground_logged_state, _last_ground_trigger_time

    frame_interval = 1.0 / cfg.STREAM_FPS
    last_frame_time = 0.0
    current_decision_label = ""
    current_detections = []
    ground_active = False
    radar_active = cfg.RADAR_SIMULATED_PROTOTYPE_STATE  # Prototype: simulated ON

    while True:
        try:
            now = asyncio.get_event_loop().time()

            # Throttle WebSocket broadcast to STREAM_FPS
            if now - last_frame_time < frame_interval:
                await asyncio.sleep(0.005)
                continue

            last_frame_time = now

            # Check ground sensor status every tick (independent of YOLO detections)
            sensor_state = sensor_provider.get_state()
            ground_active = sensor_state.ground_triggered
            raw_val = 1 if ground_active else 0
            if esp32_client.status.online:
                esp_sens = esp32_client.get_sensors()
                if esp_sens and "ground" in esp_sens:
                    g_info = esp_sens["ground"]
                    if isinstance(g_info, dict):
                        if "triggered" in g_info:
                            ground_active = bool(g_info["triggered"])
                        if "raw" in g_info:
                            raw_val = int(g_info["raw"])
                        else:
                            raw_val = 1 if ground_active else 0
                    elif isinstance(g_info, bool):
                        ground_active = g_info
                        raw_val = 1 if ground_active else 0
                if ground_active:
                    _last_ground_trigger_time = time.time()

            # Log ground status: [GROUND] GPIO26 RAW=x | TRIGGERED=YES/NO
            if ground_active != _last_ground_logged_state or ground_active:
                logger.info(f"[GROUND] GPIO26 RAW={raw_val} | TRIGGERED={'YES' if ground_active else 'NO'}")
                _last_ground_logged_state = ground_active

            # ── PATH B — GROUND SENSOR CONSECUTIVE YES LOGIC ──
            if ground_active:
                _ground_consecutive_yes += 1
                logger.info(f"[GROUND] consecutive_yes={_ground_consecutive_yes}")
                duration_sec = min(_ground_consecutive_yes, cfg.GROUND_MAX_ALARM_SECONDS)
                _ground_alarm_expires_at = time.time() + duration_sec
                if not _ground_alarm_active_state:
                    _ground_alarm_active_state = True
                    logger.info(f"[ALARM] GROUND SENSOR duration={int(duration_sec)}s")
                    event_manager.create_event(
                        track_id=None,
                        zone_id="ground-sensor",
                        class_name="ground_disturbance",
                        confidence=1.0,
                        fused_score=1.0,
                        is_critical=False,
                        reason="GROUND_SENSOR",
                        sensor_evidence={"ground_active": True, "trigger_source": "GROUND_SENSOR"},
                    )
            else:
                _ground_consecutive_yes = 0
                if _ground_alarm_active_state and time.time() >= _ground_alarm_expires_at:
                    _ground_alarm_active_state = False
                    logger.info("[BUZZER] OFF reason=GROUND_TIMEOUT")

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
                _zone_status.clear()  # Reset per-frame zone status for annotator
                current_detections = det_frame.detections

                new_label = current_decision_label

                # Per-detection processing
                for det in det_frame.detections:
                    if not det.bbox_norm:
                        continue

                    # Zone check: PERSONS use ONLY bottom-center/feet point against CAM-01 zones.
                    triggered_zones = zone_engine.check_detection(
                        det.class_name, det.bbox_norm, track_id=det.track_id, camera_id="CAM-01"
                    )
                    inside_zone = len(triggered_zones) > 0
                    zone_id = triggered_zones[0] if triggered_zones else "no-zone"

                    # ── Person zone debug logging & annotator status ────────────
                    if det.class_name == "person":
                        fx, fy = _bbox_bottom_center(det.bbox_norm)
                        logger.debug(
                            f"[ZONE] CAM-01 track={det.track_id} "
                            f"feet=({fx:.3f},{fy:.3f}) inside={inside_zone}"
                        )

                    # Fusion
                    fusion_in = FusionInput(
                        vision_confidence=det.confidence,
                        radar_triggered=radar_active,
                        ground_triggered=ground_active,
                        temporal_confirmed=False,
                        class_name=det.class_name,
                        track_id=det.track_id,
                        inside_zone=inside_zone,
                    )
                    fusion_out = fusion_engine.compute(fusion_in)

                    # Decision Engine evaluation for CAM-01
                    decision_out = decision_engine.process(
                        track_id=det.track_id,
                        zone_id=zone_id,
                        class_name=det.class_name,
                        confidence=det.confidence,
                        fused_score=fusion_out.fused_score,
                        is_confirmed_fused=fusion_out.is_confirmed,
                        decision_label=fusion_out.decision_label,
                        bbox_norm=det.bbox_norm,
                        feet_inside=inside_zone,
                        radar_triggered=radar_active,
                        ground_triggered=ground_active,
                        camera_id="CAM-01",
                    )

                    # Populate annotator status for UI live visual debug
                    if det.class_name == "person" and det.track_id is not None:
                        confirm_info = decision_engine.get_track_confirmation(
                            det.track_id, zone_id
                        )
                        st_val = "ALARM ACTIVE" if decision_out.state.value == "ALARM_ACTIVE" else "CONFIRMING" if inside_zone else "NO ALARM"
                        _zone_status[det.track_id] = {
                            "inside": inside_zone,
                            "confirm": confirm_info.get("count", 0),
                            "required": confirm_info.get("required", cfg.PERSON_CONFIRMATION_FRAMES),
                            "radar": "ON" if radar_active else "OFF",
                            "ground": "ON" if ground_active else "OFF",
                            "status": st_val,
                            "is_high_conf": (det.confidence >= cfg.YOLO_HUMAN_HIGH_CONFIDENCE),
                        }

                    if not inside_zone:
                        continue  # Outside zone — skip alarm/event creation

                    if decision_out.should_alarm or decision_out.is_critical:
                        new_label = fusion_out.decision_label

                        event_reason = (
                            "HIGH_CONFIDENCE_HUMAN_INTRUSION"
                            if decision_out.is_critical
                            else "HUMAN_INTRUSION_SENSOR_CONFIRMED"
                        )

                        if decision_out.should_alarm and det.class_name == "person":
                            logger.info(
                                f"[DECISION] CAM-01 ALARM_ACTIVE track={det.track_id} conf={det.confidence:.2f}"
                            )

                        event = None
                        if decision_out.should_create_event:
                            trigger_label = "HIGH-CONFIDENCE" if decision_out.is_critical else "YOLO + RADAR-SIM + GROUND-SENSOR"
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
                                    "radar_active": radar_active,
                                    "person_confirm_count": decision_out.person_confirm_count,
                                    "person_confirm_required": decision_out.person_confirm_required,
                                },
                            )
                            logger.info(f"[EVENT] CREATED id={event.id if event else 'COOLDOWN'}")
                            if event and decision_out.should_capture and raw_frame is not None:
                                evidence_capture.trigger(
                                    event_id=event.id,
                                    snapshot_callback=_evidence_ready_callback,
                                )

                current_decision_label = new_label

            # ── Process CAM-02 Detections & Zones if CAM-02 is Online ──────────
            cam2_b64 = ""
            raw_2 = camera_2.get_latest_raw()
            if camera_2.status.online and raw_2 is not None:
                try:
                    det2_list = detector.predict(raw_2)
                    for det2 in det2_list:
                        if not det2.bbox_norm:
                            continue
                        trig2 = zone_engine.check_detection(
                            det2.class_name, det2.bbox_norm, track_id=det2.track_id, camera_id="CAM-02"
                        )
                        inside2 = len(trig2) > 0
                        z_id2 = trig2[0] if trig2 else "no-zone"
                        fusion_in2 = FusionInput(
                            vision_confidence=det2.confidence,
                            radar_triggered=radar_active,
                            ground_triggered=ground_active,
                            temporal_confirmed=False,
                            class_name=det2.class_name,
                            track_id=det2.track_id,
                            inside_zone=inside2,
                        )
                        fusion_out2 = fusion_engine.compute(fusion_in2)
                        dec2 = decision_engine.process(
                            track_id=det2.track_id,
                            zone_id=z_id2,
                            class_name=det2.class_name,
                            confidence=det2.confidence,
                            fused_score=fusion_out2.fused_score,
                            is_confirmed_fused=fusion_out2.is_confirmed,
                            decision_label=fusion_out2.decision_label,
                            bbox_norm=det2.bbox_norm,
                            feet_inside=inside2,
                            radar_triggered=radar_active,
                            ground_triggered=ground_active,
                            camera_id="CAM-02",
                        )
                        if dec2.should_alarm and det2.class_name == "person":
                            logger.info(f"[DECISION] CAM-02 ALARM_ACTIVE track={det2.track_id} conf={det2.confidence:.2f}")

                    annotated2 = annotate_frame(
                        raw_2,
                        det2_list,
                        zone_engine.get_zones(camera_id="CAM-02"),
                        current_decision_label,
                        cfg.STREAM_JPEG_QUALITY,
                    )
                    cam2_b64 = base64.b64encode(annotated2).decode()
                except Exception as e:
                    logger.debug(f"CAM-02 processing error: {e}")
                    cam2_b64 = ""
            decision_engine.check_track_loss()

            # Check if any track remains in an active YOLO alarm state
            _yolo_alarm_active = any(
                s["state"] in ("ALARM_ACTIVE", "EVIDENCE_CAPTURE", "EVENT_ACTIVE")
                for s in decision_engine.get_all_states()
            )

            # Combined Buzzer State & Reason Arbitration
            buzzer_should_be_on = _yolo_alarm_active or _ground_alarm_active_state
            if _yolo_alarm_active and _ground_alarm_active_state:
                combined_reason = "YOLO_AND_GROUND"
            elif _yolo_alarm_active:
                combined_reason = "YOLO_HUMAN_INTRUSION"
            elif _ground_alarm_active_state:
                combined_reason = "GROUND_SENSOR"
            else:
                combined_reason = ""

            # One-Shot ESP32 Buzzer Control
            if buzzer_should_be_on and not _esp32_buzzer_on:
                _esp32_buzzer_on = True
                _buzzer_active_state = True
                _current_alarm_reason = combined_reason
                if combined_reason == "YOLO_HUMAN_INTRUSION":
                    logger.info("[ALARM] YOLO HUMAN INTRUSION")
                    logger.info(f"[BUZZER] ON reason={combined_reason}")
                elif combined_reason == "GROUND_SENSOR":
                    dur_val = int(min(_ground_consecutive_yes, cfg.GROUND_MAX_ALARM_SECONDS))
                    logger.info(f"[BUZZER] ON reason={combined_reason} duration={dur_val}s")
                else:
                    logger.info(f"[BUZZER] ON reason={combined_reason}")

                if esp32_client.status.online:
                    logger.info(f"[ESP32_REQUEST] POST /alarm active=true reason={combined_reason}")
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, esp32_client.trigger_alarm, combined_reason)

            elif not buzzer_should_be_on and _esp32_buzzer_on:
                _esp32_buzzer_on = False
                _buzzer_active_state = False
                clear_reason = "YOLO_CLEARED" if not _yolo_alarm_active else "GROUND_TIMEOUT"
                logger.info(f"[BUZZER] OFF reason={clear_reason}")
                _current_alarm_reason = ""
                if esp32_client.status.online:
                    logger.info("[ESP32_REQUEST] POST /alarm/stop")
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, esp32_client.stop_alarm)

            elif buzzer_should_be_on and _esp32_buzzer_on and combined_reason != _current_alarm_reason:
                _current_alarm_reason = combined_reason
                logger.info(f"[BUZZER] ON reason={combined_reason}")

            if raw_frame is not None:
                try:
                    annotated_jpeg = annotate_frame(
                        raw_frame,
                        current_detections,
                        zone_engine.get_zones(),
                        current_decision_label,
                        cfg.STREAM_JPEG_QUALITY,
                        zone_status=_zone_status,
                    )
                    frame_b64 = base64.b64encode(annotated_jpeg).decode()
                except Exception as e:
                    logger.debug(f"Frame annotation error: {e}")
                    frame_b64 = ""
            # Encode Camera 2 frame
            cam2_jpeg = camera_2.get_latest_jpeg()
            cam2_b64 = base64.b64encode(cam2_jpeg).decode() if cam2_jpeg else ""

            # Build stream payload with sensor telemetry status
            sensor_state_dict = {
                "radar": {
                    "triggered": True,
                    "mode": "SIMULATED",
                    "last_trigger": time.time(),
                    "health": "ok",
                    "label": "RADAR — SIMULATED / ON",
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
                "cameras": {
                    "cam_01": {
                        "id": "cam-01",
                        "name": "CAM-01 (PRIMARY)",
                        "online": camera_1.status.online,
                        "fps": round(camera_1.status.fps, 1),
                        "resolution": camera_1.status.resolution,
                        "error": camera_1.status.error,
                        "frame": frame_b64,
                    },
                    "cam_02": {
                        "id": "cam-02",
                        "name": "CAM-02 (SECONDARY)",
                        "online": camera_2.status.online,
                        "fps": round(camera_2.status.fps, 1),
                        "resolution": camera_2.status.resolution,
                        "error": camera_2.status.error or "USB CAMERA NOT DETECTED",
                        "frame": cam2_b64,
                    },
                },
                "detections": [d.to_dict() for d in current_detections],
                "zones": zone_engine.to_frontend_list(),
                "decision_state": current_decision_label,
                "sensor_state": sensor_state_dict,
                "temporal_states": decision_engine.get_all_states(),
                "buzzer_active": _buzzer_active_state or _ground_alarm_active_state,
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
        except Exception as e:
            logger.error(f"[STREAM_LOOP] Error in loop: {e}", exc_info=True)
            await asyncio.sleep(0.05)


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
