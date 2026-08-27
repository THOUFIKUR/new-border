"""
BorderPulse — Camera Capture Thread
Runs in a dedicated daemon thread.
Uses a bounded queue (maxsize=3). If inference is slow, old frames are dropped.
The camera thread is never blocked by YOLO, Supabase, or ESP32.
"""
import cv2
import threading
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("borderpulse.camera")


@dataclass
class CameraStatus:
    online: bool = False
    fps: float = 0.0
    frame_count: int = 0
    dropped_frames: int = 0
    last_frame_time: float = 0.0
    resolution: str = ""
    error: Optional[str] = None


def detect_available_cameras(max_index: int = 4) -> dict:
    """
    Scans available camera indices at startup and logs results.
    Returns dict mapping camera_index -> bool (opened).
    """
    results = {}
    logger.info("Scanning available camera hardware indices...")
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if not cap or not cap.isOpened():
            cap = cv2.VideoCapture(i)
        
        opened = cap is not None and cap.isOpened()
        results[i] = opened
        if opened:
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"[CAMERA] Available camera index {i}: YES ({w}x{h})")
            cap.release()
        else:
            logger.info(f"[CAMERA] Available camera index {i}: NO")
    return results


class CameraCapture:
    """
    Dedicated camera capture thread for real hardware cameras.

    Maintains:
    - Bounded single-slot JPEG & raw numpy frame buffer.
    - Independent FPS counter.
    - Camera health status & resolution metrics.
    """

    def __init__(self, camera_index: int = 0, camera_name: str = "CAM-01"):
        self._index = camera_index
        self._name = camera_name
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Single-slot: always holds the latest frame only
        self._latest_frame: Optional[bytes] = None  # JPEG bytes
        self._latest_raw: Optional[object] = None   # numpy array
        self._frame_lock = threading.Lock()

        self.status = CameraStatus()

        # FPS calculation
        self._fps_window = deque(maxlen=30)

    # ── Public API ───────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start hardware camera capture. Returns True if camera opened successfully."""
        if self._running:
            return True

        self._cap = cv2.VideoCapture(self._index, cv2.CAP_DSHOW)
        if not self._cap or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self._index)

        if not self._cap or not self._cap.isOpened():
            self.status.online = False
            self.status.error = "USB CAMERA NOT DETECTED"
            logger.error(f"[CAMERA] {self._name} index={self._index} FAILED — {self.status.error}")
            return False

        # Physical camera hardware connected & opened
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._cap.set(cv2.CAP_PROP_FPS, 30)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.status.resolution = f"{w}x{h}"
        self.status.online = True
        self.status.error = None

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name=f"camera-{self._index}-capture")
        self._thread.start()
        logger.info(f"[CAMERA] {self._name} started index={self._index} resolution={self.status.resolution}")
        return True

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._cap:
            self._cap.release()
        self.status.online = False
        logger.info(f"[CAMERA] {self._name} stopped")

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Returns latest JPEG frame bytes, or None if no frame yet."""
        with self._frame_lock:
            return self._latest_frame

    def get_latest_raw(self):
        """Returns latest raw numpy frame, or None."""
        with self._frame_lock:
            return self._latest_raw

    def update_frame(self, jpeg_bytes: bytes, raw_frame=None) -> bool:
        """Allows browser/cloud clients to upload camera frames directly."""
        if raw_frame is None and jpeg_bytes:
            try:
                import numpy as np
                nparr = np.frombuffer(jpeg_bytes, np.uint8)
                raw_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                logger.error(f"[CAMERA] Failed to decode injected frame: {e}")
                return False

        if raw_frame is None:
            return False

        h, w = raw_frame.shape[:2]
        now = time.monotonic()

        if jpeg_bytes is None:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
            success, buf = cv2.imencode(".jpg", raw_frame, encode_params)
            if success:
                jpeg_bytes = buf.tobytes()

        with self._frame_lock:
            self._latest_frame = jpeg_bytes
            self._latest_raw = raw_frame

        self.status.online = True
        self.status.resolution = f"{w}x{h}"
        self.status.error = None
        self.status.last_frame_time = now
        self.status.frame_count += 1

        self._fps_window.append(now)
        if len(self._fps_window) >= 2:
            elapsed = self._fps_window[-1] - self._fps_window[0]
            if elapsed > 0:
                self.status.fps = (len(self._fps_window) - 1) / elapsed
        return True

    # ── Internal ─────────────────────────────────────────────────────────

    def _capture_loop(self):
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        while self._running:
            if not self._cap or not self._cap.isOpened():
                self.status.online = False
                self.status.error = "USB CAMERA NOT DETECTED"
                time.sleep(1.0)
                continue

            ret, frame = self._cap.read()
            if not ret:
                self.status.online = False
                self.status.error = "Failed to read frame"
                time.sleep(0.1)
                continue

            now = time.monotonic()
            self.status.online = True
            self.status.error = None
            self.status.frame_count += 1
            self.status.last_frame_time = now

            success, buf = cv2.imencode(".jpg", frame, encode_params)
            if success:
                jpeg_bytes = buf.tobytes()
                with self._frame_lock:
                    self._latest_frame = jpeg_bytes
                    self._latest_raw = frame.copy()

            self._fps_window.append(now)
            if len(self._fps_window) >= 2:
                elapsed = self._fps_window[-1] - self._fps_window[0]
                if elapsed > 0:
                    self.status.fps = (len(self._fps_window) - 1) / elapsed
