# BorderPulse — Session 3: Buzzer Root-Cause, Zones, Errors, YOLO26 Upgrade, UI
**Target: Antigravity, running inside D:\hackelite**
**Supersedes nothing — this is additive to `ANTIGRAVITY_FULL_AUDIT_AND_FIX_PROMPT.md`. Read that file's Section 0
first for background, then apply the corrections below, which reflect the CURRENT code as of this session.**

---

## 0. STATE CHANGES SINCE THE LAST SESSION (verified just now)

- `SUPABASE_SERVICE_ROLE_KEY` is now a real key (no longer the placeholder). Supabase writes should be working —
  confirm live with an actual insert, don't just trust the `SUPABASE [OK]` startup log line.
- The ground sensor is now REAL, physically wired hardware — confirmed in
  `esp32/firmware/borderpulse_esp32/borderpulse_esp32.ino`: GPIO26, `INPUT_PULLUP`, `readGroundSensor()` performs a
  real `digitalRead()`, and `/sensors` correctly reports `"ground":{"mode":"REAL"}`. This is a genuine upgrade from
  the previous session — treat ground-sensor logic as real hardware now, not simulated.
- Radar is still `NOT_CONNECTED` (GPIO27 unused) — still simulated on the backend side. Don't assume otherwise.
- **Bug found: the one-time startup health banner is stale.** In `backend/app.py`, the `lifespan()` function
  hardcodes `health = {..., "ground": "SIMULATED"}` before ever checking ESP32 status, so the startup log always
  prints `GROUND SIMULATED` even now that the ground sensor is real. The *live* per-frame stream payload
  (`sensor_state_dict` further down in `_processing_loop`) correctly computes `"mode": "REAL" if
  esp32_client.status.online else "SIMULATED"` — so the frontend Sensors page is actually accurate, only the
  one-line startup log is wrong. Fix: compute the startup banner's ground/radar labels the same way, after the
  ESP32 heartbeat check completes, instead of hardcoding them before it.

---

## 1. BUZZER LOGIC — FULL TRACE AND THE CONFIRMED ROOT CAUSE OF THE UNRELIABLE ACTIVATION BUG

### 1.1 — When the buzzer is *supposed* to turn ON
In `backend/decision/engine.py`, for `class_name == "person"`:
- The person's bounding-box **bottom-center (feet) point** must be inside an enabled restricted zone
  (`feet_inside == True`). If not inside, no alarm is ever possible for that track.
- Two paths to alarm, both require `feet_inside`:
  1. **Normal path**: the same track must be confirmed inside the zone for `PERSON_CONFIRMATION_FRAMES`
     consecutive stable frames (default 4, see `.env`). A sudden bounding-box jump (`_is_bbox_stable`) resets
     this counter — this is intentional, to reject tracking glitches.
  2. **High-confidence fast path**: if `confidence >= YOLO_HUMAN_HIGH_CONFIDENCE` (default 0.85), the frame-count
     wait is skipped — but `feet_inside` is still mandatory.
- A `cooldown_seconds` gate (default 10s, `.env` `EVENT_COOLDOWN_SECONDS`) prevents immediate re-triggering.
- When these conditions are met, `decision_out.should_alarm = True`.

### 1.2 — What actually happens in `backend/app.py` when `should_alarm` fires
```python
if decision_out.should_alarm and det.class_name == "person" and not _buzzer_active_state:
    _buzzer_active_state = True   # <-- set IMMEDIATELY, before the ESP32 call even runs
    future = loop.run_in_executor(None, esp32_client.trigger_alarm, event_reason)
    future.add_done_callback(_log_esp32_result)  # logs success/failure ASYNCHRONOUSLY, afterward
```

### 1.3 — CONFIRMED ROOT CAUSE of "software alert fires but buzzer doesn't reliably activate"
`_buzzer_active_state` — the flag that drives `"buzzer_active"` in the WebSocket stream payload the frontend
reads — is set to `True` the instant the decision is made, **before** `esp32_client.trigger_alarm()` has actually
run or returned anything. The real HTTP call happens in a background executor thread and only logs its result
afterward. Two concrete ways this produces exactly the symptom you're seeing:

1. **`esp32_client.trigger_alarm()` refuses to even attempt the HTTP call if `self.status.online` is `False`**
   at that exact instant (`backend/hardware/esp32.py`, `trigger_alarm()` — `if not self.status.online: return False`
   with zero HTTP attempt). `status.online` is only updated by a heartbeat thread every `ESP32_HEARTBEAT_INTERVAL`
   seconds (5s by default). If the intrusion event happens to land inside a brief window where the last heartbeat
   failed (e.g. a hotspot hiccup — your ESP32 is on a phone hotspot SSID, which is exactly the kind of network
   that has brief dropouts), the buzzer command is silently never sent — yet the UI already shows
   `buzzer_active: true` because that flag was set before any of this was checked.
2. Even when the HTTP call is attempted and fails (non-200, timeout, connection reset), the failure is logged
   (`[BUZZER] FAILED — hardware unavailable`) but nothing reverts `_buzzer_active_state` back to `False`, so the
   UI keeps showing the alarm as active regardless.

**This is a real, fixable bug, not a hardware wiring problem.** Fix required:
- Do not set `_buzzer_active_state = True` optimistically. Set a separate `_buzzer_command_sent = True` at
  request time, and only set `_buzzer_active_state = True` inside `_log_esp32_result` once `fut.result()` is
  confirmed `True` (i.e. ESP32 actually returned HTTP 200).
- Update the frontend/stream payload to expose three distinct states, matching the audit's Section 7
  requirement: `alert_decided`, `alarm_command_sent`, `buzzer_acknowledged` — don't collapse them into one
  boolean. Never claim the buzzer is on unless `buzzer_acknowledged` is true.
- Consider raising `ESP32_RETRY_COUNT` and/or shortening `ESP32_HEARTBEAT_INTERVAL` given the hotspot network,
  and/or having `trigger_alarm()` attempt the HTTP call directly even if the cached `status.online` is stale, since
  a real request is a more current signal than a heartbeat up to 5 seconds old. Do not remove the heartbeat, just
  don't let it gate an actual alarm attempt.

### 1.4 — When the buzzer turns OFF
- Software side: when no track remains in `ALARM_ACTIVE`/`EVIDENCE_CAPTURE`/`EVENT_ACTIVE` state (person left the
  zone, or `check_track_loss()` clears a track that hasn't been seen for `TRACK_LOSS_GRACE_SECONDS`), `app.py`
  sends `POST /alarm/stop` once.
- Hardware side, independent of the above: the firmware's own `checkAlarmTimeout()` turns the buzzer off once
  `millis() >= alarmEndTime` (set from `duration_ms` in the original `/alarm` request, default 5000ms) — this is
  a correct hardware-side safety net and should be left as-is.

---

## 2. RESTRICTED ZONE — HOW CREATE/DELETE WORK RIGHT NOW (both are already implemented correctly)

**Create a zone:**
1. Open the Zones page. Click **"+ Draw Zone"**.
2. Click at least 3 points directly on the live camera image to place polygon vertices (canvas coordinates are
   converted to normalized 0–1 camera-space, correctly accounting for letterbox/pillarbox aspect-ratio padding —
   this logic in `Zones.jsx`'s `getDisplayDimensions()`/`handleClick()` is already correct).
3. Type a name in the text box that appears, click **"Save (N pts)"**. This calls `POST /api/zones`, which
   requires ≥3 points, persists to Supabase, and adds it to the live `zone_engine`.

**Delete a zone:** click the red **"Delete"** button next to the zone in the list below the canvas, confirm the
browser prompt. This calls `DELETE /api/zones/{id}`, which removes it from both the live engine and Supabase.

**This UI is already well-built** — smooth two-layer canvas (static camera layer + `requestAnimationFrame`
interaction layer), mouse movement never triggers React re-renders, coordinates are stored in camera-native
normalized space. If zone drawing still feels laggy to the user in practice, do not rewrite this component —
instead profile it live first (check `STREAM_FPS`/JPEG decode cost on the camera layer's `Image.onload`, which
re-decodes a full JPEG on every WebSocket frame even while not drawing a new zone) and only optimize the actual
bottleneck found. A likely real fix: skip re-drawing the camera layer's `<img>` decode when the zone editor isn't
the active page/tab, and/or throttle it below full `STREAM_FPS` since 15fps of full JPEG decode per frame on the
main thread is unnecessary for a background reference image.

---

## 3. RUNTIME ERRORS FROM THE ATTACHED LOG — DIAGNOSIS

```
[STREAM_LOOP] Error in loop: name 'dead' is not defined
UnboundLocalError: local variable 'ws' referenced before assignment
NameError: name 'dead' is not defined
```
The current `_processing_loop()` in `backend/app.py` (WebSocket broadcast section, near the end) already reads:
```python
if _active_ws_clients:
    msg = json.dumps(stream_payload)
    dead = []
    for ws in _active_ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _active_ws_clients.remove(ws)
```
This is structurally correct — `dead` is defined before the loop, `ws` is properly scoped as the loop variable.
**This specific crash may already be resolved** in the current file version; the log the user captured may be
from an earlier run. Confirm by reproducing: start the app, open the frontend, and watch for this exact error
again. If it still occurs, the likely cause is a *different* code path setting `dead`/`ws` inconsistently under a
race (e.g., two coroutines mutating `_active_ws_clients` at once) — add a lock or copy the list
(`for ws in list(_active_ws_clients):`) defensively regardless, since iterating a list while another task can
mutate it is fragile even if this exact trace doesn't reproduce.

```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000):
only one usage of each socket address (protocol/network address/port) is normally permitted
```
This is **not a code bug** — it's Windows reporting that port 8000 is already in use, almost certainly by a
previous BorderPulse backend process that's still running (e.g., from an earlier terminal that wasn't closed, or
a crashed process that didn't release the port). Tell the user directly: run
`netstat -ano | findstr :8000` in PowerShell, find the PID in the last column, then `taskkill /PID <pid> /F`,
then restart the backend. Also add a startup check to `app.py`/the run script: before calling `uvicorn.run(...)`,
attempt to bind the port first and print a clear "port already in use — is another instance running?" message
instead of letting the raw `OSError` propagate past `Application startup complete` (which is confusingly printed
*before* the bind failure in the log — the FastAPI lifespan already finished, then uvicorn failed to bind,
which is why the log looks like it started successfully and then died).

---

## 4. UPGRADE YOLO11n → YOLO26n

Confirmed via current Ultralytics documentation: YOLO26 is a real, released model family (January 2026),
faster and more accurate than YOLO11 at every scale, with native end-to-end NMS-free inference — a good fit for
this project's low-latency requirement. YOLO26n specifically benchmarks ~43% faster CPU inference than YOLO11n.

Steps:
1. Confirm the installed `ultralytics` package version in `requirements.txt` supports YOLO26 — check the current
   installed version (`pip show ultralytics`) against Ultralytics' YOLO26 release notes; upgrade the package if
   needed (`pip install -U ultralytics`).
2. Change `.env`: `YOLO_MODEL=models/yolo/yolo26n.pt`. The weights auto-download on first load the same way
   `yolo11n.pt` did — confirm `backend/vision/detector.py`'s `load()` path handles this without change (it
   should, since it just passes the path/name to `YOLO()`).
3. YOLO26 is NMS-free by design — check whether `backend/vision/detector.py` does any manual NMS/IOU
   post-processing that assumed YOLO11's output format, and remove/adjust it if it's now redundant or conflicts.
   `YOLO_IOU=0.45` in `.env` may become a no-op for YOLO26 — verify against the loaded model's own inference
   call rather than assuming.
4. COCO class IDs (80 classes) are unchanged between YOLO11 and YOLO26, so `backend/vision/detector.py`'s class
   filtering (person/animal/vehicle allow-list) should not need remapping — verify with one live test per class
   family (person, a vehicle class, one animal class) rather than assuming.
5. Re-run the full detection/tracking/zone test suite after swapping models — a faster, more confident model can
   change how quickly `PERSON_CONFIRMATION_FRAMES` is reached, which is fine, but confirm no threshold in
   `.env` needs retuning as a result (e.g., confidence scores may shift distribution slightly).
6. Keep `models/yolo/yolo11n.pt` in place as a fallback — don't delete it — in case YOLO26n introduces a
   regression discovered late in testing; make the swap a one-line `.env` change, not a hard-coded path change,
   so reverting is instant during the hackathon if needed.

---

## 5. UI CHANGES

The user wants UI changes but has not yet specified exactly what. Do not do a broad redesign speculatively.
Apply these specific, low-risk improvements now (all directly justified by bugs/gaps found above), then ask the
user what additional UI changes they want before doing anything larger:

- **Sensors page / Live Monitor**: show the buzzer's three-stage status distinctly — "Alert Decided" →
  "Alarm Sent" → "Buzzer Confirmed" (per Section 1.3's fix) — instead of a single on/off indicator. This
  directly reflects the real hardware truth instead of the optimistic flag.
- **Sensors page**: ground sensor should visually read "GROUND — REAL HARDWARE (GPIO26)" when
  `esp32_client.status.online` is true (the data already supports this — `sensor_state_dict["ground"]["label"]`
  already computes this correctly; just confirm the frontend renders that `label` field rather than a
  hardcoded string).
- **Startup/health log**: fix the stale "GROUND SIMULATED" banner per Section 0.
- **Zones page**: while the create/delete flow already works, add a small on-canvas hint distinguishing "zone
  save succeeded locally" vs "zone save succeeded in Supabase" — right now a Supabase write failure is silently
  swallowed (`except Exception: pass` in `backend/api/zones.py`'s `create_zone`), so a zone could appear to save
  in the UI but not actually persist to the cloud. Surface that failure instead of swallowing it.

Ask the user directly: **what specific pages or elements do they want changed, and in what way** (layout,
color/theme, information density, mobile responsiveness, something else)? Do not guess further than the
above without that answer.

---

## 6. EXECUTION ORDER FOR THIS SESSION

1. Fix the port-8000 issue is a user action (Section 3) — not code. Tell the user directly, don't spend agent
   time on it beyond adding the clearer startup error message.
2. Fix the buzzer three-state tracking bug (Section 1.3) — highest priority, this is the actual root cause of
   the most demo-critical symptom.
3. Fix the stale startup health banner (Section 0).
4. Confirm the WebSocket loop crash doesn't still reproduce (Section 3); harden with `list(_active_ws_clients)`
   regardless.
5. Swap to YOLO26n (Section 4), re-run the full test suite.
6. Surface Supabase zone-save failures instead of swallowing them (Section 5).
7. Report back with logs proving the buzzer now correctly distinguishes decided/sent/acknowledged on a real
   test run, before asking the user for further UI direction.
