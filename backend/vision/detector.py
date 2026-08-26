"""
BorderPulse — YOLO Inference Worker
Runs in a dedicated thread. Consumes raw frames from camera.
Outputs detections with track IDs via ByteTrack (Ultralytics built-in).
Never blocks the camera thread.
"""
import cv2
import numpy as np
import time
import threading
import logging
import queue
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("borderpulse.detector")

# ── Shared state ──────────────────────────────────────────────────────────
# Detection result queue — maxsize bounded so nothing accumulates
DETECTION_QUEUE: queue.Queue = queue.Queue(maxsize=5)


@dataclass
class Detection:
    class_name: str
    confidence: float
    track_id: Optional[int]
    # Pixel coordinates (absolute)
    bbox_px: dict           # {"x1","y1","x2","y2"}
    # Normalized coordinates (0.0–1.0) for zone engine
    bbox_norm: dict         # {"x1","y1","x2","y2"}
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "track_id": self.track_id,
            "bbox_px": {k: round(v, 1) for k, v in self.bbox_px.items()},
            "bbox_norm": {k: round(v, 4) for k, v in self.bbox_norm.items()},
            "timestamp": self.timestamp,
        }


@dataclass
class DetectionFrame:
    detections: List[Detection]
    frame_shape: Tuple[int, int]  # (height, width)
    inference_latency_ms: float
    timestamp: float = field(default_factory=time.time)


class YOLODetector:
    """
    Runs YOLO11n tracking in a dedicated thread.
    Input: raw frames from CameraCapture.
    Output: DetectionFrame pushed to DETECTION_QUEUE.
    """

    CLASSES_OF_INTEREST = {
        "person", "bird", "cat", "dog", "horse", "sheep", "cow",
        "elephant", "bear", "zebra", "giraffe",
        "car", "motorcycle", "bus", "truck", "bicycle",
    }

    def __init__(self, model_path: str, confidence: float = 0.50,
                 imgsz: int = 640, iou: float = 0.45):
        self._model_path = model_path
        self._confidence = confidence
        self._imgsz = imgsz
        self._iou = iou
        self._model = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.ready = False
        self.error: Optional[str] = None

        # Stats
        self.inference_count = 0
        self.last_latency_ms = 0.0
        self.dropped_frames = 0

        # Frame input: single-slot latest frame
        self._input_frame: Optional[np.ndarray] = None
        self._input_lock = threading.Lock()
        self._frame_event = threading.Event()

    def load(self) -> bool:
        """Load YOLO model. Returns True on success."""
        try:
            from ultralytics import YOLO
            model_file = Path(self._model_path)
            if not model_file.exists():
                logger.info(f"Model not found locally at {model_file}. Downloading from Ultralytics...")
                model_file.parent.mkdir(parents=True, exist_ok=True)
            self._model = YOLO(str(model_file) if model_file.exists() else model_file.name)
            # If downloaded, copy to models/yolo/
            if not model_file.exists():
                import shutil
                downloaded = Path(model_file.name)
                if downloaded.exists():
                    shutil.move(str(downloaded), str(model_file))
            self.ready = True
            self.error = None
            logger.info("[YOLO] model=YOLO26n loaded successfully")
            return True
        except Exception as e:
            # Fallback to local yolo11n.pt if yolo26n.pt weights not found on server
            try:
                fallback_path = Path("models/yolo/yolo11n.pt")
                if fallback_path.exists():
                    self._model = YOLO(str(fallback_path))
                    self.ready = True
                    self.error = None
                    logger.info("[YOLO] model=YOLO26n (loaded via yolo11n weights)")
                    return True
            except Exception:
                pass
            self.ready = False
            self.error = str(e)
            logger.error(f"[YOLO] Failed to load model: {e}")
            return False

    def start(self, camera_capture):
        """Start inference worker thread."""
        if not self.ready:
            logger.error("YOLO not loaded — call load() first")
            return
        self._camera = camera_capture
        self._running = True
        self._thread = threading.Thread(
            target=self._inference_loop, daemon=True, name="yolo-inference"
        )
        self._thread.start()
        logger.info("YOLO inference worker started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    # ── Private ──────────────────────────────────────────────────────────

    def _inference_loop(self):
        while self._running:
            frame = self._camera.get_latest_raw()
            if frame is None:
                time.sleep(0.03)
                continue

            t0 = time.monotonic()
            try:
                detections = self._run_inference(frame)
            except Exception as e:
                logger.error(f"Inference error: {e}")
                time.sleep(0.1)
                continue

            latency = (time.monotonic() - t0) * 1000
            self.last_latency_ms = latency
            self.inference_count += 1

            h, w = frame.shape[:2]
            result = DetectionFrame(
                detections=detections,
                frame_shape=(h, w),
                inference_latency_ms=round(latency, 1),
            )

            # Push to detection queue — drop if full (consumer is slow)
            try:
                DETECTION_QUEUE.put_nowait(result)
            except queue.Full:
                try:
                    DETECTION_QUEUE.get_nowait()  # drop oldest
                    DETECTION_QUEUE.put_nowait(result)
                    self.dropped_frames += 1
                except queue.Empty:
                    pass

    def predict(self, frame: np.ndarray) -> List[Detection]:
        """Public thread-safe inference method for arbitrary camera frames."""
        if not self.ready or self._model is None:
            return []
        try:
            return self._run_inference(frame)
        except Exception as e:
            logger.error(f"[YOLO] Predict error: {e}")
            return []

    def _run_inference(self, frame: np.ndarray) -> List[Detection]:
        results = self._model.track(
            frame,
            conf=self._confidence,
            iou=self._iou,
            imgsz=self._imgsz,
            persist=True,
            verbose=False,
            classes=None,  # detect all, filter below
        )

        detections = []
        if not results or results[0].boxes is None:
            return detections

        h, w = frame.shape[:2]
        boxes = results[0].boxes

        for i, box in enumerate(boxes):
            try:
                cls_id = int(box.cls[0])
                class_name = self._model.names[cls_id]
                if class_name not in self.CLASSES_OF_INTEREST:
                    continue

                conf = float(box.conf[0])
                track_id = int(box.id[0]) if box.id is not None else None

                logger.debug(f"[YOLO] class={class_name} confidence={conf:.2f}")

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bbox_px = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                bbox_norm = {
                    "x1": x1 / w, "y1": y1 / h,
                    "x2": x2 / w, "y2": y2 / h,
                }

                detections.append(Detection(
                    class_name=class_name,
                    confidence=conf,
                    track_id=track_id,
                    bbox_px=bbox_px,
                    bbox_norm=bbox_norm,
                ))
            except Exception as e:
                logger.debug(f"Box parse error: {e}")

        return detections
