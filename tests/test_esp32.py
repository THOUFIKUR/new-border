"""
BorderPulse — ESP32 Client Unit Tests
All network calls are mocked. No physical ESP32 required.
For a real-hardware test, use scripts/test_esp32_connection.py instead.
"""
import time
import httpx
import pytest
from unittest.mock import patch, MagicMock

import backend.config as cfg
from backend.hardware.esp32 import ESP32Client


def make_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


def test_base_url_construction():
    client = ESP32Client()
    assert client._base_url == f"http://{cfg.ESP32_IP}:{cfg.ESP32_PORT}"


def test_heartbeat_success_marks_online():
    client = ESP32Client()
    ok_resp = make_response(200, {"firmware": "0.1.0-prototype"})
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = ok_resp
        client._check_status()
    assert client.status.online is True
    assert client.status.firmware_version == "0.1.0-prototype"
    assert client.status.error is None


def test_heartbeat_failure_marks_offline_after_retries():
    client = ESP32Client()
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError("refused")
        with patch("time.sleep"):  # skip retry delay in test
            client._check_status()
    assert client.status.online is False
    assert client.status.error is not None


def test_heartbeat_retries_before_giving_up():
    """A transient single failure followed by success should NOT mark offline."""
    client = ESP32Client()
    ok_resp = make_response(200, {"firmware": "0.1.0-prototype"})
    call_count = {"n": 0}

    def flaky_get(url):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.TimeoutException("timeout")
        return ok_resp

    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.side_effect = flaky_get
        with patch("time.sleep"):
            client._check_status()
    assert client.status.online is True
    assert call_count["n"] >= 2


def test_alarm_blocked_when_offline():
    client = ESP32Client()
    client.status.online = False
    result = client.trigger_alarm(reason="test")
    assert result is False


def test_alarm_sent_when_online():
    client = ESP32Client()
    client.status.online = True
    ok_resp = make_response(200)
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = ok_resp
        result = client.trigger_alarm(reason="human_intrusion", duration_ms=5000)
    assert result is True
    assert client.status.buzzer_active is True


def test_alarm_payload_matches_firmware_contract():
    """Backend payload keys must exactly match what the .ino firmware expects."""
    client = ESP32Client()
    client.status.online = True
    ok_resp = make_response(200)
    with patch("httpx.Client") as MockClient:
        mock_post = MockClient.return_value.__enter__.return_value.post
        mock_post.return_value = ok_resp
        client.trigger_alarm(reason="human_intrusion", duration_ms=5000)
    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert set(payload.keys()) == {"active", "reason", "duration_ms"}
    assert payload["active"] is True
    assert payload["reason"] == "human_intrusion"
    assert payload["duration_ms"] == 5000


def test_alarm_marks_offline_on_exception():
    client = ESP32Client()
    client.status.online = True
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("refused")
        result = client.trigger_alarm(reason="test")
    assert result is False
    assert client.status.online is False


def test_reconnect_after_offline():
    """OFFLINE -> heartbeat succeeds -> ONLINE."""
    client = ESP32Client()
    client.status.online = False
    ok_resp = make_response(200, {"firmware": "0.1.0-prototype"})
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = ok_resp
        client._check_status()
    assert client.status.online is True


def test_get_sensors_returns_none_when_offline():
    client = ESP32Client()
    client.status.online = False
    assert client.get_sensors() is None
