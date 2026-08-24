"""
BorderPulse — ESP32 HTTP Client
Communicates with ESP32 over Wi-Fi REST API.
Non-blocking: camera and vision pipeline continue if ESP32 is offline.
Implements heartbeat, timeout, and automatic reconnect detection.
"""
import httpx
import asyncio
import logging
import time
import threading
from typing import Optional
import backend.config as cfg

logger = logging.getLogger("borderpulse.esp32")


class ESP32Status:
    def __init__(self):
        self.online: bool = False
        self.last_seen: float = 0.0
        self.firmware_version: Optional[str] = None
        self.ip: str = cfg.ESP32_IP
        self.error: Optional[str] = None
        self.buzzer_active: bool = False

    def to_dict(self) -> dict:
        return {
            "online": self.online,
            "ip": self.ip,
            "last_seen": self.last_seen,
            "firmware_version": self.firmware_version,
            "error": self.error,
            "buzzer_active": self.buzzer_active,
            "label": "ESP32 ONLINE" if self.online else "ESP32 OFFLINE",
        }


class ESP32Client:
    """
    HTTP REST client for ESP32.
    All network calls are non-blocking (run in executor thread).
    If ESP32 is unreachable, status.online = False and vision continues normally.
    """

    def __init__(self):
        self.status = ESP32Status()
        self._base_url = f"http://{cfg.ESP32_IP}:{cfg.ESP32_PORT}"
        self._timeout = cfg.ESP32_TIMEOUT
        self._heartbeat_interval = cfg.ESP32_HEARTBEAT_INTERVAL
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """Start heartbeat thread."""
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="esp32-heartbeat",
        )
        self._heartbeat_thread.start()
        logger.info(f"ESP32 client started. Target: {self._base_url}")

    def stop(self):
        self._running = False

    def _heartbeat_loop(self):
        while self._running:
            self._check_status()
            time.sleep(self._heartbeat_interval)

    def _check_status(self):
        """
        Attempt a status check with configurable retries before marking the
        device offline. A single dropped packet/transient timeout on a
        mobile-hotspot network should not immediately flip the badge to
        OFFLINE and block alarm delivery.
        """
        url = f"{self._base_url}/status"
        last_error = None
        attempts = max(1, cfg.ESP32_RETRY_COUNT)
        for attempt in range(1, attempts + 1):
            start = time.time()
            logger.debug(f"[ESP32_REQUEST] method=GET url={url} attempt={attempt}")
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    r = client.get(url)
                latency_ms = int((time.time() - start) * 1000)
                if r.status_code == 200:
                    data = r.json()
                    self.status.online = True
                    self.status.last_seen = time.time()
                    self.status.firmware_version = data.get("firmware", "unknown")
                    self.status.error = None
                    logger.debug(f"[ESP32_RESPONSE] status=200 latency_ms={latency_ms}")
                    return
                else:
                    last_error = f"HTTP {r.status_code}"
                    logger.debug(f"[ESP32_RESPONSE] status={r.status_code} latency_ms={latency_ms}")
            except Exception as e:
                last_error = str(e)
                logger.debug(f"[ESP32_ERROR] type={type(e).__name__} message={e}")
            if attempt < attempts:
                time.sleep(cfg.ESP32_RETRY_DELAY)
        self._mark_offline(last_error or "unknown error")

    def _mark_offline(self, reason: str):
        if self.status.online:
            logger.warning(f"ESP32 went OFFLINE: {reason}")
        self.status.online = False
        self.status.error = reason

    def trigger_alarm(self, reason: str = "intrusion", duration_ms: int = 5000) -> bool:
        """
        Send alarm command to ESP32.
        Non-blocking. Returns False if ESP32 is offline.
        """
        if not self.status.online:
            logger.warning(f"[BUZZER] FAILED — ESP32 OFFLINE, alarm not requested (reason={reason})")
            return False
        url = f"{self._base_url}/alarm"
        payload = {"active": True, "reason": reason, "duration_ms": duration_ms}
        logger.info(f"[ESP32_REQUEST] method=POST url={url} reason={reason} duration_ms={duration_ms}")
        try:
            start = time.time()
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(url, json=payload)
            latency_ms = int((time.time() - start) * 1000)
            if r.status_code == 200:
                self.status.buzzer_active = True
                logger.info(f"[ESP32_RESPONSE] status=200 latency_ms={latency_ms}")
                logger.info(f"[BUZZER] ACKNOWLEDGED reason={reason}")
                return True
            else:
                logger.warning(f"[ESP32_RESPONSE] status={r.status_code} latency_ms={latency_ms}")
                logger.warning(f"[BUZZER] FAILED — ESP32 returned HTTP {r.status_code}")
        except Exception as e:
            logger.error(f"[ESP32_ERROR] type={type(e).__name__} message={e}")
            logger.error(f"[BUZZER] FAILED — request exception")
            self._mark_offline(str(e))
        return False

    def stop_alarm(self) -> bool:
        if not self.status.online:
            return False
        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(f"{self._base_url}/alarm/stop")
                self.status.buzzer_active = False
                return r.status_code == 200
        except Exception as e:
            logger.error(f"Failed to stop ESP32 alarm: {e}")
        return False

    def test_buzzer(self) -> bool:
        if not self.status.online:
            logger.warning("Test buzzer failed — ESP32 OFFLINE")
            return False
        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(f"{self._base_url}/test/buzzer")
                return r.status_code == 200
        except Exception as e:
            logger.error(f"Test buzzer error: {e}")
        return False

    def get_sensors(self) -> Optional[dict]:
        if not self.status.online:
            return None
        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.get(f"{self._base_url}/sensors")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.debug(f"Get sensors error: {e}")
        return None
