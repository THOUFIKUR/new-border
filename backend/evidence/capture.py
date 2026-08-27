"""
BorderPulse — Evidence Capture
Ring buffer for pre-event frames.
On trigger: freeze pre-buffer, capture post-event, write snapshot + video.
Does NOT continuously write frames to disk.
"""
import cv2
import os
import time
import threading
import logging
import queue
from collections import deque
from pathlib import Path
from typing import Optional, List
import numpy as np

logger = logging.getLogger("borderpulse.evidence")


class EvidenceCapture:
    """
    Pre/post event buffer.
    Thread-safe ring buffer maintains last N seconds of frames.
    On trigger: dumps pre-buffer + continues capturing post-event frames.
    """

    def __init__(
        self,
        local_dir: Path,
        pre_event_seconds: float = 5.0,
        post_event_seconds: float = 8.0,
        target_fps: float = 15.0,
    ):
        self._local_dir = local_dir
        self._pre_secs = pre_event_seconds
        self._post_secs = post_event_seconds
        self._fps = target_fps

        # Ring buffer capacity
        max_pre_frames = int(pre_event_seconds * target_fps) + 10
        self._pre_buffer: deque = deque(maxlen=max_pre_frames)
        self._buffer_lock = threading.Lock()

        # Capture state
        self._capturing = False
        self._capture_thread: Optional[threading.Thread] = None
        self._post_frames: List[np.ndarray] = []
        self._post_frame_queue: queue.Queue = queue.Queue(maxsize=200)

        # Ensure output directories exist
        (local_dir / "images").mkdir(parents=True, exist_ok=True)
        (local_dir / "videos").mkdir(parents=True, exist_ok=True)

    def push_frame(self, frame: np.ndarray):
        """Called every inference cycle to maintain the pre-buffer."""
        with self._buffer_lock:
            self._pre_buffer.append((time.time(), frame.copy()))

        # If actively capturing post-event frames, also feed them
        if self._capturing:
            try:
                self._post_frame_queue.put_nowait(frame.copy())
            except queue.Full:
                pass  # Drop if post buffer is full

    def trigger(self, event_id: str, snapshot_callback=None) -> Optional[dict]:
        """
        Trigger evidence capture.
        Returns immediately; capture finishes in background thread.
        Returns paths dict once snapshot is done.
        """
        if self._capturing:
            logger.warning("Evidence capture already in progress — ignoring trigger")
            return None

        # Snapshot: take immediately from latest pre-buffer frame
        snapshot_path = self._save_snapshot(event_id)

        # Start post-event video capture in background
        with self._buffer_lock:
            pre_frames = list(self._pre_buffer)

        self._capturing = True
        self._capture_thread = threading.Thread(
            target=self._capture_post_event,
            args=(event_id, pre_frames, snapshot_path, snapshot_callback),
            daemon=True,
            name=f"evidence-{event_id[:8]}",
        )
        self._capture_thread.start()

        return {"snapshot_path": str(snapshot_path), "event_id": event_id}

    def _save_snapshot(self, event_id: str) -> Path:
        with self._buffer_lock:
            if not self._pre_buffer:
                return None
            _, frame = self._pre_buffer[-1]

        path = self._local_dir / "images" / f"{event_id}_snapshot.jpg"
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        cv2.imwrite(str(path), frame, encode_params)
        logger.info(f"Snapshot saved: {path}")
        return path

    def _capture_post_event(self, event_id: str, pre_frames: list,
                             snapshot_path: Optional[Path], callback):
        """Captures post-event frames and encodes the full clip."""
        post_deadline = time.monotonic() + self._post_secs
        post_frames = []

        while time.monotonic() < post_deadline:
            try:
                frame = self._post_frame_queue.get(timeout=0.1)
                post_frames.append(frame)
            except queue.Empty:
                pass

        self._capturing = False

        # Determine frame size
        all_frames = [f for _, f in pre_frames] + post_frames
        if not all_frames:
            logger.warning("No frames to encode for evidence video")
            return

        h, w = all_frames[0].shape[:2]
        video_path = self._local_dir / "videos" / f"{event_id}_clip.mp4"

        try:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(video_path), fourcc, self._fps, (w, h))
            for frame in all_frames:
                if frame.shape[:2] == (h, w):
                    writer.write(frame)
            writer.release()
            logger.info(f"Evidence video saved: {video_path} ({len(all_frames)} frames)")
        except Exception as e:
            logger.error(f"Failed to encode evidence video: {e}")
            video_path = None

        if callback:
            try:
                callback(event_id, snapshot_path, video_path)
            except Exception as e:
                logger.error(f"Evidence callback error: {e}")
