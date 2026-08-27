# BorderPulse — Testing Guide

---

## Quick Test: Run Unit Tests

```powershell
cd d:\hackelite
python -m pytest tests/ -v
```

**Expected output:**
```
tests/test_decision.py::test_fusion_critical_vision_only PASSED
tests/test_decision.py::test_fusion_confirmed_with_all_sensors PASSED
tests/test_decision.py::test_fusion_possible_vision_only_low PASSED
tests/test_decision.py::test_fusion_radar_not_human_identity PASSED
tests/test_decision.py::test_fusion_weights_configurable PASSED
tests/test_decision.py::test_decision_high_confidence_immediate_alarm PASSED
tests/test_decision.py::test_decision_temporal_path PASSED
tests/test_decision.py::test_decision_cooldown PASSED
tests/test_decision.py::test_decision_different_tracks_independent PASSED
tests/test_decision.py::test_event_manager_cooldown PASSED
tests/test_decision.py::test_event_manager_acknowledge PASSED
tests/test_zones.py::test_point_inside_square PASSED
tests/test_zones.py::test_point_outside_square PASSED
...
========================= 24 passed in 0.24s =========================
```

---

## System Integration Tests

Run these in order with both backend and frontend running.

### TEST 1 — API Health Check

```powershell
python -c "
import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')
r = urllib.request.urlopen('http://localhost:8000/api/health', timeout=5)
data = json.loads(r.read())
print('Camera online:', data['camera']['online'])
print('Camera FPS:', data['camera']['fps'])
print('YOLO ready:', data['yolo']['ready'])
print('Supabase:', data['supabase']['connected'])
print('ESP32:', data['esp32']['online'])
"
```

**Expected:**
```
Camera online: True
Camera FPS: ~15.0
YOLO ready: True
Supabase: True
ESP32: False   ← OK if not connected yet
```

---

### TEST 2 — WebSocket Live Stream

Open browser console at http://localhost:5173/ and run:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/stream');
ws.onmessage = (e) => {
  const d = JSON.parse(e.data);
  console.log('Frame:', !!d.frame, 'Dets:', d.detections?.length, 'Decision:', d.decision_state);
};
```

**Expected:** Continuous messages with `frame: true`, detection count, and decision state.

---

### TEST 3 — Camera Test

```powershell
python -c "
import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')
r = urllib.request.urlopen('http://localhost:8000/api/camera/health', timeout=5)
data = json.loads(r.read())
print('State:', data.get('camera_health', {}).get('state'))
print('FPS:', data.get('camera_health', {}).get('fps'))
print('Resolution:', data.get('camera_status', {}).get('resolution'))
"
```

**Expected:** `State: HEALTHY`, FPS > 10, Resolution: 1280x720

---

### TEST 4 — Zone Create Test

```powershell
python -c "
import urllib.request, json
data = json.dumps({
    'name': 'Test Zone',
    'polygon_points': [
        {'x': 0.2, 'y': 0.2}, {'x': 0.8, 'y': 0.2},
        {'x': 0.8, 'y': 0.8}, {'x': 0.2, 'y': 0.8}
    ],
    'zone_type': 'restricted',
    'enabled': True,
    'alert_on_classes': ['person']
}).encode()
req = urllib.request.Request('http://localhost:8000/api/zones', data=data, headers={'Content-Type': 'application/json'}, method='POST')
r = urllib.request.urlopen(req)
resp = json.loads(r.read())
print('Zone created:', resp.get('zone', {}).get('id'))
"
```

**Expected:** Zone ID printed (UUID)

---

### TEST 5 — Synthetic Event Test

```powershell
python -c "
import urllib.request, json
req = urllib.request.Request('http://localhost:8000/api/test/event', method='POST', headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
resp = json.loads(r.read())
print('Event created:', resp)
"
```

**Expected:**
```
Event created: {'success': True, 'event_id': 'BP-...', 'message': 'Test event created'}
```

Then open http://localhost:5173/events — you should see the test event appear.

---

### TEST 6 — Sensor Simulation Test

```powershell
python -c "
import urllib.request, json
data = json.dumps({'radar': True, 'ground': True}).encode()
req = urllib.request.Request('http://localhost:8000/api/sensors/simulate', data=data, headers={'Content-Type': 'application/json'}, method='POST')
r = urllib.request.urlopen(req)
print(json.loads(r.read()))
"
```

**Expected:**
```
{'success': True, 'radar_triggered': True, 'ground_triggered': True}
```

Check http://localhost:5173/sensors — both should show TRIGGERED.

Then reset:
```powershell
python -c "
import urllib.request, json
data = json.dumps({'radar': False, 'ground': False}).encode()
req = urllib.request.Request('http://localhost:8000/api/sensors/simulate', data=data, headers={'Content-Type': 'application/json'}, method='POST')
urllib.request.urlopen(req)
print('Reset OK')
"
```

---

### TEST 7 — Person-in-Zone Detection Test (Manual)

1. Start backend + frontend
2. Go to http://localhost:5173/zones
3. Draw a polygon zone that covers most of the camera view
4. Go to http://localhost:5173/monitor
5. Step in front of the camera
6. Watch:
   - Detection box appears with track ID
   - Decision state changes from MONITORING → POSSIBLE DETECTION → TEMPORAL CONFIRMATION → CONFIRMED
   - If confidence ≥ 0.85 AND inside zone → immediate CRITICAL INTRUSION
7. Check http://localhost:5173/events — event should appear

---

### TEST 8 — Evidence Capture Test

After triggering a zone intrusion event:

1. Go to http://localhost:5173/events
2. Click on the event
3. Scroll to **Evidence Media** section
4. Check: snapshot visible? Video visible?
5. If Storage upload failed, check local files:
   ```
   d:\hackelite\evidence\snapshots\  ← should contain .jpg files
   d:\hackelite\evidence\videos\     ← should contain .mp4 files
   ```

---

### TEST 9 — Supabase Data Test

Check that events are written to Supabase:

1. Go to https://app.supabase.com
2. Open your project → Table Editor → **events** table
3. You should see event records after triggering intrusions

---

### TEST 10 — ESP32 Test (After Flashing)

After connecting ESP32 and setting ESP32_IP in .env:

```powershell
python -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8000/api/esp32/status', timeout=5)
data = json.loads(r.read())
print('ESP32 online:', data.get('online'))
print('IP:', data.get('ip'))
print('Firmware:', data.get('firmware_version'))
"
```

**Expected:**
```
ESP32 online: True
IP: 192.168.x.x
Firmware: BorderPulse v1.0
```

Then test buzzer:
```powershell
python -c "
import urllib.request, json
data = json.dumps({'active': True, 'reason': 'test', 'duration_ms': 2000}).encode()
req = urllib.request.Request('http://localhost:8000/api/esp32/alarm', data=data, headers={'Content-Type': 'application/json'}, method='POST')
r = urllib.request.urlopen(req)
print(json.loads(r.read()))
"
```

**Expected:** Buzzer sounds for 2 seconds on the ESP32.

---

### TEST 11 — Failure / Graceful Degradation Tests

| Test | How | Expected Behavior |
|------|-----|------------------|
| Camera disconnected | Stop backend, unplug cam, restart | "CAMERA OFFLINE" in dashboard, YOLO stops, no crash |
| ESP32 offline | Don't connect or set wrong IP | "ESP32 OFFLINE" in dashboard, vision continues |
| Supabase unreachable | Revoke service key temporarily | Events saved locally, error logged, no crash |
| Backend stopped | Ctrl+C backend | Frontend shows "BACKEND OFFLINE", WebSocket auto-reconnects |

---

## Full End-to-End Workflow Test

The primary validation test:

```
1. Start backend                        → Watch startup log
2. Start frontend                       → Open http://localhost:5173/
3. Draw restricted zone (Zones page)   → Polygon saved in Supabase
4. Step in front of camera             → YOLO detects person
5. Enter the zone                      → Decision engine triggers
6. Wait for TEMPORAL CONFIRMATION       → 3 frames in 1 second
7. HIGH CONFIDENCE (≥0.85)             → Immediate CRITICAL INTRUSION
8. Check Events page                   → Event appears
9. Click event                         → See snapshot + fusion evidence
10. Check Supabase events table        → Row created
11. Check Supabase Storage             → Image/video uploaded
12. If ESP32 connected: buzzer sounds  → 3-second alarm
13. Click Acknowledge on dashboard     → Status changes
14. Click Resolve                      → Event closed
```

All 14 steps passing = full system operational.
