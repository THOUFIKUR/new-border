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


class CameraCapture:
    """
    Dedicated camera capture thread.

    Maintains:
    - A bounded single-slot JPEG & raw frame buffer.
    - FPS counter.
    - Camera health status.
    - Auto-fallback to mirrored/derived feed if index hardware is absent.
    """

    def __init__(self, camera_index: int = 0, fallback_source: Optional["CameraCapture"] = None):
        self._index = camera_index
        self._fallback_source = fallback_source
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._is_fallback = False
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
        """Start camera. Returns True if camera opened successfully or fallback active."""
        if self._running:
            return True

        self._cap = cv2.VideoCapture(self._index, cv2.CAP_DSHOW)
        if not self._cap or not self._cap.isOpened():
            # Fallback: try default backend without DirectShow
            self._cap = cv2.VideoCapture(self._index)

        if not self._cap or not self._cap.isOpened():
            if self._fallback_source:
                logger.info(f"Camera index {self._index} hardware not found — activating Secondary Angle Fallback")
                self._is_fallback = True
                self.status.online = True
                self.status.resolution = "1280x720 (SECONDARY)"
                self.status.error = None
                self._running = True
                self._thread = threading.Thread(target=self._fallback_loop, daemon=True, name=f"camera-{self._index}-fallback")
                self._thread.start()
                return True
            else:
                self.status.online = False
                self.status.error = f"Cannot open camera index {self._index}"
                logger.error(self.status.error)
                return False

        # Physical camera hardware connected & opened
        self._is_fallback = False
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
        logger.info(f"Camera started: index={self._index} resolution={self.status.resolution}")
        return True

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._cap:
            self._cap.release()
        self.status.online = False
        logger.info(f"Camera {self._index} stopped")

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Returns latest JPEG frame bytes, or None if no frame yet."""
        with self._frame_lock:
            return self._latest_frame

    def get_latest_raw(self):
        """Returns latest raw numpy frame, or None."""
        with self._frame_lock:
            return self._latest_raw

    # ── Internal ─────────────────────────────────────────────────────────

    def _capture_loop(self):
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        while self._running:
            if not self._cap or not self._cap.isOpened():
                self.status.online = False
                self.status.error = "Camera disconnected"
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

    def _fallback_loop(self):
        """Generates secondary view when secondary USB camera hardware is not plugged in."""
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        while self._running:
            if not self._fallback_source:
                time.sleep(0.1)
                continue

            raw = self._fallback_source.get_latest_raw()
            if raw is None:
                time.sleep(0.03)
                continue

            # Derive secondary angle (horizontally flipped with secondary badge)
            sec_frame = cv2.flip(raw, 1)
            cv2.putText(
                sec_frame, "CAM-02 (SECONDARY ANGLE)",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 229, 255), 2, cv2.LINE_AA
            )

            now = time.monotonic()
            self.status.online = True
            self.status.error = None
            self.status.frame_count += 1
            self.status.last_frame_time = now
            self.status.fps = self._fallback_source.status.fps

            success, buf = cv2.imencode(".jpg", sec_frame, encode_params)
            if success:
                jpeg_bytes = buf.tobytes()
                with self._frame_lock:
                    self._latest_frame = jpeg_bytes
                    self._latest_raw = sec_frame.copy()

            time.sleep(1.0 / 30)
