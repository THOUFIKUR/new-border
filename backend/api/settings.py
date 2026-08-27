"""BorderPulse — Settings API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class FusionWeights(BaseModel):
    vision: float
    radar: float
    ground: float
    temporal: float
    confirmed_threshold: float


class DecisionConfig(BaseModel):
    min_frames: int
    window_seconds: float
    cooldown_seconds: float
    human_high_confidence: float


class YOLOConfig(BaseModel):
    confidence: float
    human_high_confidence: float
    imgsz: Optional[int] = None


@router.get("/settings")
async def get_settings():
    from backend.app import fusion_engine, decision_engine
    import backend.config as cfg
    return {
        "fusion": {
            "w_vision": fusion_engine.w_vision,
            "w_radar": fusion_engine.w_radar,
            "w_ground": fusion_engine.w_ground,
            "w_temporal": fusion_engine.w_temporal,
            "confirmed_threshold": fusion_engine.confirmed_threshold,
        },
        "decision": {
            "min_frames": decision_engine.min_frames,
            "window_seconds": decision_engine.window_seconds,
            "cooldown_seconds": decision_engine.cooldown_seconds,
            "human_high_confidence": decision_engine.human_high_confidence,
        },
        "yolo": {
            "model": cfg.YOLO_MODEL,
            "confidence": cfg.YOLO_CONFIDENCE,
            "human_high_confidence": cfg.YOLO_HUMAN_HIGH_CONFIDENCE,
            "imgsz": cfg.YOLO_IMGSZ,
        },
        "capture": {
            "pre_event_seconds": cfg.PRE_EVENT_SECONDS,
            "post_event_seconds": cfg.POST_EVENT_SECONDS,
        },
        "stream": {
            "fps": cfg.STREAM_FPS,
            "jpeg_quality": cfg.STREAM_JPEG_QUALITY,
        },
        "runtime": {
            "mode": cfg.RUNTIME_MODE,
            "sensor_simulation": cfg.SENSOR_SIMULATION,
        },
    }


@router.put("/settings/fusion")
async def update_fusion(body: FusionWeights):
    from backend.app import fusion_engine
    fusion_engine.update_weights(
        w_vision=body.vision,
        w_radar=body.radar,
        w_ground=body.ground,
        w_temporal=body.temporal,
        confirmed_threshold=body.confirmed_threshold,
    )
    return {"success": True, "fusion": body.dict()}


@router.put("/settings/decision")
async def update_decision(body: DecisionConfig):
    from backend.app import decision_engine
    decision_engine.update_config(
        min_frames=body.min_frames,
        window_seconds=body.window_seconds,
        cooldown_seconds=body.cooldown_seconds,
        human_high_confidence=body.human_high_confidence,
    )
    return {"success": True, "decision": body.dict()}


@router.post("/test/event")
async def test_event():
    """Create a synthetic test event."""
    from backend.app import event_manager
    event = event_manager.create_event(
        track_id=9999,
        zone_id="test-zone",
        class_name="person",
        confidence=0.92,
        fused_score=0.92,
        is_critical=True,
        reason="TEST EVENT",
        sensor_evidence={"test": True},
    )
    if event:
        return {"success": True, "event": event.to_dict(), "note": "TEST MODE"}
    return {"success": False, "note": "Cooldown active — wait 10s"}


@router.post("/test/buzzer")
async def test_buzzer():
    from backend.app import esp32_client
    ok = esp32_client.test_buzzer()
    if not ok:
        return {"success": False, "note": "ESP32 OFFLINE — buzzer not activated"}
    return {"success": True, "note": "Test buzzer sent to ESP32"}


@router.get("/camera/health")
async def camera_health():
    from backend.app import camera, health_monitor
    raw = camera.get_latest_raw()
    if raw is not None:
        metrics = health_monitor.analyse(raw, camera.status.fps)
    else:
        metrics = health_monitor.get_last()
    return {
        "camera_health": health_monitor.to_dict(),
        "camera_status": camera.status.online,
        "resolution": camera.status.resolution,
        "frame_count": camera.status.frame_count,
        "dropped_frames": camera.status.dropped_frames,
    }


@router.get("/analytics/summary")
async def analytics_summary():
    from backend.app import event_manager, detector, camera
    import time
    events = event_manager.get_all_events()
    now = time.time()
    one_hour_ago = now - 3600
    today_midnight = now - (now % 86400)

    by_type = {}
    by_severity = {}
    for e in events:
        t = e.event_type.value
        s = e.severity.value
        by_type[t] = by_type.get(t, 0) + 1
        by_severity[s] = by_severity.get(s, 0) + 1

    events_last_hour = sum(1 for e in events if e.started_at >= one_hour_ago)
    events_today = sum(1 for e in events if e.started_at >= today_midnight)
    false_positives = sum(1 for e in events if e.status.value == "false_positive")
    avg_conf = sum(e.confidence for e in events) / len(events) if events else 0

    return {
        "total_events": len(events),
        "events_last_hour": events_last_hour,
        "events_today": events_today,
        "by_type": by_type,
        "by_severity": by_severity,
        "false_positives": false_positives,
        "avg_confidence": round(avg_conf, 3),
        "inference_count": detector.inference_count,
        "camera_fps": round(camera.status.fps, 1),
        "camera_uptime": camera.status.online,
    }
