"""
BorderPulse — Frame Annotator
Draws bounding boxes, labels, track IDs and restricted zones on frames.
Returns annotated JPEG bytes for streaming.
"""
import cv2
import numpy as np
from typing import List, Optional
from backend.vision.detector import Detection
from backend.vision.zones import Zone


# Color palette per class (BGR)
CLASS_COLORS = {
    "person": (0, 50, 255),      # Red
    "car": (255, 165, 0),        # Orange
    "truck": (255, 100, 0),      # Dark orange
    "motorcycle": (200, 100, 0),
    "bicycle": (150, 200, 0),
    "bus": (200, 50, 0),
    "bird": (0, 220, 100),       # Green
    "cat": (0, 200, 150),
    "dog": (0, 180, 180),
}
DEFAULT_COLOR = (0, 200, 200)
ZONE_COLOR = (0, 100, 255)       # Amber for zone outline
ZONE_FILL_ALPHA = 0.15

THREAT_COLORS = {
    "CRITICAL HUMAN INTRUSION": (0, 0, 255),
    "CONFIRMED INTRUSION": (0, 50, 200),
    "PROBABLE INTRUSION": (0, 100, 200),
    "POSSIBLE DETECTION": (0, 180, 200),
}


def annotate_frame(
    frame: np.ndarray,
    detections: List[Detection],
    zones: List[Zone],
    decision_label: str = "",
    jpeg_quality: int = 75,
    zone_status: Optional[dict] = None,
) -> bytes:
    """
    Annotate a frame with detections and zone overlays.
    zone_status: optional dict keyed by track_id:
      {track_id: {"inside": bool, "confirm": int, "required": int}}
      When provided, the feet dot is colored (red=inside, green=outside)
      and the label shows zone membership + confirmation count.
    Returns JPEG bytes.
    """
    h, w = frame.shape[:2]
    annotated = frame.copy()

    # Draw restricted zones (filled polygon overlay)
    overlay = annotated.copy()
    for zone in zones:
        if not zone.enabled or len(zone.polygon_points) < 3:
            continue
        pts = np.array(
            [(int(p.x * w), int(p.y * h)) for p in zone.polygon_points],
            dtype=np.int32,
        )
        cv2.fillPoly(overlay, [pts], ZONE_COLOR)
        cv2.polylines(annotated, [pts], True, ZONE_COLOR, 2)
        # Zone label
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        cv2.putText(annotated, zone.name, (cx - 30, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.addWeighted(overlay, ZONE_FILL_ALPHA, annotated, 1 - ZONE_FILL_ALPHA, 0, annotated)

    # Draw detections
    for det in detections:
        color = CLASS_COLORS.get(det.class_name, DEFAULT_COLOR)
        x1 = int(det.bbox_px["x1"])
        y1 = int(det.bbox_px["y1"])
        x2 = int(det.bbox_px["x2"])
        y2 = int(det.bbox_px["y2"])

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Bottom-center contact point (feet marker)
        bx = (x1 + x2) // 2
        # Color by zone membership when status is available:
        #   RED   = feet inside restricted zone (alarm risk)
        #   GREEN = feet outside zone (safe)
        #   YELLOW = no zone status (default / no zones configured)
        if det.class_name == "person" and zone_status is not None and det.track_id is not None:
            st = zone_status.get(det.track_id, {})
            inside = st.get("inside", None)
            if inside is True:
                dot_color = (0, 0, 255)    # Red  — inside zone
            elif inside is False:
                dot_color = (0, 255, 0)    # Green — outside zone
            else:
                dot_color = (0, 255, 255)  # Yellow — unknown
        else:
            dot_color = (0, 255, 255)      # Yellow default
        cv2.circle(annotated, (bx, y2), 5, dot_color, -1)

        # Label — for persons include zone status, confirmation count, radar, ground, and decision status
        track_str = f"#{det.track_id}" if det.track_id is not None else ""
        if det.class_name == "person" and zone_status is not None and det.track_id is not None:
            st = zone_status.get(det.track_id, {})
            inside = st.get("inside", None)
            confirm = st.get("confirm", 0)
            required = st.get("required", 4)
            radar_str = st.get("radar", "ON")
            ground_str = st.get("ground", "ON")
            status_str = st.get("status", "NO ALARM")
            is_high = st.get("is_high_conf", False)

            if inside is True:
                if is_high:
                    label = f"PERSON {det.confidence:.2f} {track_str} | ZONE: IN | STATUS: HIGH-CONFIDENCE ALARM"
                elif status_str == "ALARM ACTIVE":
                    label = f"PERSON {det.confidence:.2f} {track_str} | ZONE: IN | CONFIRM: {confirm}/{required} | RADAR: {radar_str} | GROUND: {ground_str} | STATUS: ALARM ACTIVE"
                else:
                    label = f"PERSON {det.confidence:.2f} {track_str} | ZONE: IN | CONFIRM: {confirm}/{required} | RADAR: {radar_str} | GROUND: {ground_str} | STATUS: {status_str}"
            elif inside is False:
                label = f"PERSON {det.confidence:.2f} {track_str} | ZONE: OUT | CONFIRM: 0/{required} | RADAR: {radar_str} | GROUND: {ground_str} | STATUS: NO ALARM"
            else:
                label = f"person {det.confidence:.2f} {track_str}"
        else:
            label = f"{det.class_name} {det.confidence:.2f} {track_str}"
        label_y = max(y1 - 8, 15)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(annotated, (x1, label_y - th - 4), (x1 + tw + 4, label_y + 4), color, -1)
        cv2.putText(annotated, label, (x1 + 2, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    # Threat status overlay (top-left)
    if decision_label:
        threat_color = THREAT_COLORS.get(decision_label, (200, 200, 200))
        cv2.rectangle(annotated, (0, 0), (420, 36), (0, 0, 0), -1)
        cv2.putText(annotated, f"⚡ {decision_label}", (8, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, threat_color, 2)

    # Encode to JPEG
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    _, buf = cv2.imencode(".jpg", annotated, encode_params)
    return buf.tobytes()
