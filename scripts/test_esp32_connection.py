"""
BorderPulse — ESP32 Network Diagnostic Script
================================================
Standalone reachability test, independent of the running backend.
Reads ESP32_IP / ESP32_PORT from backend.config (which loads .env) —
never hardcode the IP here.

Usage:
    python scripts/test_esp32_connection.py
    python scripts/test_esp32_connection.py --alarm-test   # also fires a real (short) alarm test

Exit code 0 = ESP32 fully reachable and responding correctly.
Exit code 1 = one or more layers failed.
"""
import sys
import time
import argparse
import socket
from pathlib import Path

# Allow running as `python scripts/test_esp32_connection.py` from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import backend.config as cfg  # noqa: E402

try:
    import httpx
except ImportError:
    print("httpx is required: pip install httpx")
    sys.exit(1)


def test_tcp(ip: str, port: int, timeout: float = 3.0) -> tuple[bool, str]:
    start = time.time()
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            latency_ms = int((time.time() - start) * 1000)
            return True, f"{latency_ms} ms"
    except socket.timeout:
        return False, "TIMEOUT"
    except ConnectionRefusedError:
        return False, "CONNECTION REFUSED"
    except OSError as e:
        return False, f"OS ERROR: {e}"


def test_http(url: str, method: str = "GET", timeout: float = 3.0, json_body=None):
    start = time.time()
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                r = client.get(url)
            else:
                r = client.post(url, json=json_body or {})
        latency_ms = int((time.time() - start) * 1000)
        return True, r.status_code, latency_ms, r
    except httpx.TimeoutException:
        return False, None, None, "TIMEOUT"
    except httpx.ConnectError as e:
        return False, None, None, f"CONNECT ERROR: {e}"
    except Exception as e:
        return False, None, None, f"ERROR: {e}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alarm-test", action="store_true",
                         help="Also send a real /test/buzzer request (audible beep on ESP32)")
    args = parser.parse_args()

    ip = cfg.ESP32_IP
    port = cfg.ESP32_PORT
    base = f"http://{ip}:{port}"

    print("=" * 55)
    print(f"ESP32 TARGET: {ip}:{port}")
    print("=" * 55)

    overall_ok = True

    # 1. TCP reachability
    tcp_ok, tcp_detail = test_tcp(ip, port)
    print(f"\nTCP CONNECT ({ip}:{port}):")
    print(f"  {'PASS' if tcp_ok else 'FAIL'} — {tcp_detail}")
    overall_ok &= tcp_ok

    if not tcp_ok:
        print("\nTCP layer failed — skipping HTTP tests.")
        print("Check: laptop/ESP32 on same subnet, Windows Firewall, AP/client isolation.")
        print(f"\nESP32 ONLINE: NO")
        sys.exit(1)

    # 2. HTTP root
    ok, status, latency, resp = test_http(f"{base}/")
    print(f"\nHTTP GET / :")
    if ok:
        print(f"  PASS — HTTP {status}, {latency} ms")
    else:
        print(f"  FAIL — {resp}")
    overall_ok &= ok

    # 3. /status endpoint (verified to exist in firmware)
    ok, status, latency, resp = test_http(f"{base}/status")
    print(f"\nSTATUS ENDPOINT (GET /status):")
    if ok and status == 200:
        print(f"  PASS — HTTP {status}, latency={latency} ms")
        try:
            data = resp.json()
            print(f"  JSON valid — firmware={data.get('firmware')} uptime_ms={data.get('uptime_ms')}")
        except Exception:
            print("  WARNING — response was not valid JSON")
            overall_ok = False
    elif ok:
        print(f"  FAIL — endpoint reachable but returned HTTP {status}")
        overall_ok = False
    else:
        print(f"  FAIL — {resp}")
        overall_ok = False

    # 4. Optional: real buzzer test (least invasive is /status; /test/buzzer is audible/physical)
    if args.alarm_test:
        print(f"\nTEST BUZZER (POST /test/buzzer) — this WILL sound the physical buzzer:")
        ok, status, latency, resp = test_http(f"{base}/test/buzzer", method="POST")
        if ok and status == 200:
            print(f"  PASS — HTTP {status}, latency={latency} ms")
        else:
            print(f"  FAIL — {resp if not ok else f'HTTP {status}'}")
            overall_ok = False
    else:
        print("\nTEST BUZZER: SKIPPED (pass --alarm-test to run it)")

    print("\n" + "=" * 55)
    print(f"ESP32 ONLINE: {'YES' if overall_ok else 'NO'}")
    print("=" * 55)

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
