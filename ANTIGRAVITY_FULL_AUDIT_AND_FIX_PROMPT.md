# BorderPulse — Full Audit & Fix Execution Prompt
**Target: Antigravity, running inside D:\hackelite**
**This file is the single source of truth for this work session. Read it fully before changing anything.**

---

## 0. VERIFIED CURRENT STATE (checked directly against the files in this repo moments before this prompt was written — do not assume otherwise)

Two things the user believes are fixed are **not** fixed yet. Confirm these first, before trusting anything else in this document or in the user's own description of "current problems":

1. **`.env` still has a placeholder service-role key:**
   `SUPABASE_SERVICE_ROLE_KEY=REPLACE_WITH_SERVICE_ROLE_KEY_FROM_SUPABASE_DASHBOARD`
   As of the last audit, `backend/database/supabase_client.py` explicitly checks for this placeholder and returns `None` instead of a client, which silently disables every database write. This is almost certainly still true. Verify it live, report it if still broken, and tell the user exactly where to paste the real key (`.env`, backend only) — do not ask them to paste the key value into chat or into any file you show back to them.

2. **`.env` has `SENSOR_SIMULATION=true`, and the ESP32 firmware
   (`esp32/firmware/borderpulse_esp32/borderpulse_esp32.ino`) still declares `radarTriggered` /
   `groundTriggered` as hardcoded `bool` variables that are never set by any `digitalRead()` call.**
   The firmware's own `/sensors` handler returns `"mode": "NOT_CONNECTED"` for both, and the source comments
   explicitly say `// FUTURE: read from PIN_RADAR_OUT` / `// Future — not connected yet`.
   **This means: whatever the user is currently seeing as "radar/ground triggering" in the UI is coming
   from the `SimulatedSensorProvider` toggle on the Sensors page, not from real physical sensors — even
   though the user believes the sensors are wired and active.** Confirm this directly with the user before
   doing any hardware-side sensor work: ask whether they have physically soldered/connected an RCWL-0516
   and a ground-vibration sensor to GPIO27/GPIO26 on the ESP32, and flashed updated firmware that reads them.
   If not, real GPIO sensor reading is a feature that still needs to be built (see Section 6), not a bug to
   fix — don't spend time debugging "why doesn't my real sensor value show up" when no code path reads a
   real sensor yet.

Do not let either of these assumptions leak into the rest of the audit. Re-verify both at the start of your
session and state plainly which is actually true right now.

---

## 1. PROJECT IDENTITY — DO NOT REBUILD

This is BorderPulse, an existing, mostly-working false-alarm-resilient border/restricted-area surveillance
system. Camera capture, YOLO detection + tracking, the zone engine, sensor fusion, the decision state
machine, evidence capture, the ESP32 HTTP client, and all 10 frontend pages are real, already-working
implementations — confirmed by direct code inspection in a prior audit. **Do not rebuild any of this from
scratch. Do not replace working modules, APIs, UI, or ESP32 communication unless you have reproduced a
specific bug and traced it to that exact module.** Every change must be the smallest safe fix that
addresses a proven root cause, followed by re-running tests.

---

## 2. CURRENT USER-OBSERVED PROBLEMS (to verify, not assume)

- ESP32 connects; manual `/test/buzzer` works.
- Radar/ground sensor status appears active/triggered in the UI (see Section 0 — verify whether this is
  simulated or real before treating it as a hardware bug).
- Human detection produces a bounding box.
- Human inside the restricted zone can produce a software alert, but the **physical buzzer does not
  reliably activate** on a real intrusion event (even though the manual test works). This is the top
  priority bug — see Section 7.
- Object class (person/animal/bird/vehicle/etc.) is not reliably shown/propagated to the UI.
- Camera zoom/focus behavior does not work as expected.
- Snapshot capture is not reliable.
- Video capture is not reliable.
- Evidence is not reliably stored in Supabase (likely explained by Section 0, item 1 — confirm).
- Restricted-zone polygon drawing is laggy/inaccurate.
- Event/database/evidence/hardware states are not reliably synchronized.

---

## 3. SUPABASE — CONFIGURATION IN USE (public-safe values only)

```
SUPABASE_URL=https://frmisnduadstnjwyyvym.supabase.co
```
The anon/publishable key currently in `.env` is already a real (non-placeholder) JWT-format key — this is
safe to use as-is and safe to expose to frontend code by design (Supabase anon/publishable keys are meant
to be public, unlike the service-role key). Note: the user also mentioned a newer-format
`sb_publishable_...` style key at one point — these are two different valid Supabase key formats
(legacy JWT anon key vs. new publishable-key format). Don't treat this as a conflict; either works. Confirm
which one the current Supabase project actually expects and use that.

**Hard rules, no exceptions:**
- Never request, print, log, or write the `SUPABASE_SERVICE_ROLE_KEY` value anywhere — not in chat, not in
  any file, not in a commit, not in a screenshot.
- Never put the service-role key in frontend code.
- Never commit `.env`. Only ever write variable *names* (not values) into `.env.example`.
- If the service-role key is still a placeholder, report that plainly as a blocker and tell the user the
  exact steps to fix it (Supabase dashboard → Project Settings → API → service_role key → paste into local
  `.env` → restart backend) without asking them to paste the value into chat.
- Use the connected Supabase tooling to inspect the *current* schema, tables, RLS policies, and storage
  buckets before creating or migrating anything. Do not drop tables. Do not recreate the database. Use
  additive migrations only.
- Do a real insert + read test and a real storage upload test once the key is fixed — don't just claim
  "Supabase connected" because credentials exist.

Expected logical entities (verify existing names before renaming anything):
`detection_events` (or `events`), `sensor_events` (or `sensor_readings`), `zones`, `system_status`.
Expected storage buckets: `event-images`, `event-videos` (confirm exact names already in use).

---

## 4. FULL CODEBASE AUDIT (re-run, don't assume the last one still holds)

Inspect `backend/`, `frontend/`, `esp32/`, `tests/`, `docs/`, `.env`/`.env.example`, `requirements.txt`,
`package.json`, and any Supabase migrations. For every file that's actually imported/called at runtime
(trace imports — don't assume a file is live just because it exists), report: path, purpose, inputs,
outputs, key classes/functions, current status, bugs found, proposed fix.

Re-check every finding from the previous audit — some may already be fixed, don't blindly re-apply old
fixes:
- Supabase service-role placeholder disabling writes (Section 0 — likely still true)
- Radar/ground-only fusion unreachable when YOLO has zero detections in a frame
- Evidence E2E test checking `evidence_local/snapshots` while capture writes to `evidence_local/images`
- ESP32 chip-ID verification missing at boot
- Missing group-activity detection (`EventType.GROUP_ACTIVITY` declared but never triggered)
- Missing `BehaviourProvider` interface
- Missing rain sensor path
- Partial/no offline Supabase write queue
- Missing zone-boundary hysteresis
- Missing PTZ adapter interface
- Missing Raspberry Pi runtime branch
- Missing explainability panel, attack/demo simulation, confidence timeline, zone heatmap

---

## 5. OBJECT CLASSIFICATION — MAKE IT RELIABLE

Verify the full path: YOLO model → class IDs → confidence threshold → filtering → tracker → backend
event `object_class` field → frontend rendering. At minimum distinguish person, car, truck, bus,
motorcycle, bicycle, dog, cat, bird, other/unknown. Never label radar/ground motion as a human identity —
that's vision's job, not the sensors'. A normal RGB webcam cannot see thermal radiation — do not fake
thermal capability. Keep the current RGB+YOLO path working; add a clean, currently-unimplemented
`ThermalCameraProvider` interface for later.

---

## 6. RESTRICTED-ZONE DRAWING — FIX LAG/ACCURACY

Requirements: smooth point insertion, correct screen-to-camera coordinate transform (including
aspect-ratio/letterbox handling), draggable/deletable points, undo, close/reset/cancel, live inside/outside
preview, save/reload exact coordinates in camera-native space (not raw browser pixel space), avoid
self-intersection where practical. Add tests for the coordinate conversion and for point-in-polygon
membership specifically.

---

## 7. TOP PRIORITY BUG — ESP32 BUZZER DOESN'T FIRE ON REAL INTRUSION

Manual `/test/buzzer` works; real intrusion alerts don't reliably reach the buzzer. Trace the entire chain
end to end and add structured logs at each hop so this is debuggable going forward:

```
decision engine -> event creation -> alarm decision -> backend/hardware/esp32.py
  -> HTTP POST /alarm -> ESP32 receives JSON -> digitalWrite(PIN_BUZZER, HIGH) -> buzzer
```

Check specifically:
- Is an alarm command actually generated for this event's severity, or is the event type/severity being
  filtered out before it reaches the ESP32 client?
- Is the ESP32 IP/port in `.env` correct and reachable from the backend process at the moment of the alert
  (not just at heartbeat time)?
- What's the actual HTTP response status and body from `/alarm`? Is it ever non-200 and swallowed?
- Is there a race condition (e.g., cooldown logic suppressing the alarm call right after a heartbeat check)?
- Is any exception around the `/alarm` POST caught and silently logged instead of surfaced?
- Does the frontend show "alert" based only on the *decision*, before confirming the ESP32 actually
  acknowledged it? If so, that's misleading — fix the UI to distinguish three separate states:
  **ALERT DECIDED → ALARM COMMAND SENT → BUZZER ACKNOWLEDGED**. Never claim the buzzer activated unless the
  ESP32's HTTP response actually confirms it.

Add log lines tagged `[DECISION]`, `[EVENT]`, `[ESP32_REQUEST]`, `[ESP32_RESPONSE]`, `[BUZZER]` so a real
run can be traced afterward.

---

## 8. CAMERA ZOOM/FOCUS

Confirm the actual camera hardware in use (fixed USB webcam vs. anything else). If it's a fixed webcam, do
not claim optical/PTZ zoom — implement or fix **digital crop/zoom**, clearly labeled "Digital Zoom" in the
UI, and always preserve the original full-resolution frame for evidence (crop/zoom is a secondary view
only). If real PTZ hardware exists, build the adapter interface (`move_to_zone`, `zoom_in`, `zoom_out`,
`return_home`) — otherwise leave it as a clearly-labeled future interface.

---

## 9. SNAPSHOT + VIDEO EVIDENCE

Verify the full path: pre-event ring buffer → snapshot → post-event recording → local finalization →
Supabase upload → DB reference → frontend retrieval. Confirm local paths actually used are
`evidence_local/images/` and `evidence_local/videos/` — fix any test or code still referencing
`evidence_local/snapshots/`. Evidence capture must never block detection. If cloud upload fails: keep the
local file, mark the event `upload_failed`, queue a retry, never lose the event.

---

## 10. SENSOR FUSION — MUST RUN INDEPENDENTLY OF THE YOLO LOOP

Radar and ground sensors provide physical/motion evidence, never identity. The fusion/decision path for
"radar and/or ground triggered but no visual confirmation" must execute on its own — it cannot be nested
only inside the per-YOLO-detection loop, or it can never fire when there's zero detections in a frame
(this was the exact bug found in the previous audit — confirm whether it's fixed).

Expected outcomes:
- Radar + ground + person + inside zone + temporal confirmation → high-confidence intrusion
- Radar only, no visual target → suspicious motion, not human
- Ground only → ground disturbance
- Person outside zone → detection logged, no intrusion
- Animal in zone → animal intrusion / environmental event
- Vehicle in zone → vehicle intrusion

---

## 11. EVENT TYPES

Use explicit types: `HUMAN_INTRUSION`, `VEHICLE_INTRUSION`, `ANIMAL_INTRUSION`, `SUSPICIOUS_MOTION`,
`GROUND_DISTURBANCE`, `GROUP_ACTIVITY`, `SYSTEM_FAULT`, `CAMERA_FAULT`, `SENSOR_FAULT`. Never call an
animal a human. Never call radar/ground motion a human detection.

---

## 12. GROUP ACTIVITY

If ≥3 distinct person track IDs are simultaneously inside the same zone → `GROUP_ACTIVITY`. Never claim
"fighting" or abnormal behavior without a real, evaluated behavior model.

---

## 13. EXPLAINABILITY PANEL

Add to Event Detail: object class + confidence, zone, radar state, ground state, temporal confirmation
count, decision score/severity, ESP32 alarm status (decided/sent/acknowledged — see Section 7), snapshot
status, video status, Supabase upload status. Example target layout:

```
PERSON 0.91
Inside Restricted Zone 1
Radar YES   Ground YES   Temporal 4/5
Decision HIGH
ESP32 ACK
Snapshot UPLOADED   Video UPLOADED
```

---

## 14. OFFLINE/FAILURE HANDLING

Handle gracefully, without crashing: Supabase offline, ESP32 offline, camera disconnected, YOLO failure,
video failure, Wi-Fi failure. ESP32 offline → log a software event, retain evidence locally, show OFFLINE
in the UI, keep running. Supabase offline → retain event/evidence locally, queue retry, sync later.

---

## 15. TESTING

Create/run tests for: person / animal / vehicle classification; zone coordinate transform; polygon
membership; zone-boundary hysteresis; radar-only; ground-only; radar+ground; person outside zone; person
inside zone; person+radar; person+radar+ground; ESP32 alarm; ESP32 unavailable; snapshot; video; Supabase
insert; Supabase upload; Supabase retry; full end-to-end intrusion.

Build one **full demo test**: radar trigger → ground trigger → person detection → zone entry → temporal
confirmation → high confidence → event → ESP32 alarm request → evidence capture → Supabase write. This
should be runnable on demand as your live hackathon demo script.

---

## 16. SECURITY CHECKLIST

- Service-role key never in frontend, React source, public env, Git history, screenshots, or docs.
- Backend-only access to the service-role key.
- If frontend needs Supabase access, use the anon/publishable key with RLS enforcing access control.

---

## 17. RASPBERRY PI / THERMAL ROADMAP (do not implement now — interface only)

Keep laptop mode stable. Define `RUNTIME_MODE=raspberry_pi` as a future path. Camera abstraction:
`CameraProvider` → `RGBCameraProvider` (current, real) and `ThermalCameraProvider` (future, not
implemented — do not fake thermal imaging in software).

---

## 18. UNIQUE HACKATHON FEATURES — EVALUATE AND IMPLEMENT WHERE SAFE, IN THIS ORDER

For each, report impact / difficulty / risk / demo value before building:
1. Explainable sensor-fusion score (Section 13)
2. Adaptive confidence threshold
3. Zone-specific thresholds
4. Multi-frame confirmation (should already partly exist — verify)
5. Sensor agreement score
6. False-alarm reason classification
7. Environmental event log
8. Offline evidence queue (Section 14)
9. Event replay/demo mode
10. Attack/demo simulation panel
11. Zone heatmap
12. Live confidence timeline
13. Multi-camera abstraction
14. RGB+thermal fusion interface (interface only, Section 17)
15. Camera-health score
16. Sensor-health score

---

## 19. HOW TO WORK — ONE FIX AT A TIME

For every change: reproduce the bug → identify root cause → make the smallest safe fix → re-run tests →
report the result before moving to the next item. Do not batch multiple unrelated fixes into one pass. Do
not rewrite the whole project. Do not replace YOLO, the frontend framework, existing APIs, evidence logic,
or ESP32 support unless a proven bug requires it.

**Execution order for this session:**
1. Confirm Section 0 findings live (Supabase key, sensor simulation vs real) — report status before anything else.
2. Fix Section 7 (ESP32 buzzer on real intrusion) — highest priority, most demo-visible bug.
3. Fix Section 9 (evidence capture/upload) and Section 3 (Supabase writes) together, since they're linked.
4. Fix Section 5 (object classification display) and Section 6 (zone drawing).
5. Fix Section 10 (independent radar/ground fusion path).
6. Add Section 13 (explainability panel) and Section 12 (group activity) — both are close to already-existing code.
7. Run Section 15's full demo test end to end.
8. Only then, if time remains, work through Section 18's remaining feature list in order.

---

## 20. FINAL REPORT REQUIRED AT THE END OF THIS SESSION

Produce: executive summary; architecture; full folder tree; file-by-file purpose/status; working features;
previous bugs; newly found bugs; fixed bugs; remaining bugs; Supabase status; ESP32 status; camera status;
YOLO status; sensor status; zone status; evidence status; DB/storage status; test results; end-to-end
result; hardware limitations; thermal roadmap; Raspberry Pi roadmap; unique features status; demo sequence;
exact setup steps; environment **variable names only** (never values); security checklist; performance
metrics; false-alarm evaluation methodology; final **READY / NOT READY** verdict.

Label every feature: **WORKING / PARTIALLY WORKING / BROKEN / SIMULATED / NOT IMPLEMENTED / HARDWARE
REQUIRED**. If hardware can't be verified in this session, say so explicitly: "HARDWARE NOT AVAILABLE —
SOFTWARE PATH VERIFIED ONLY."

**Start now: confirm Section 0, then proceed through Section 19's execution order, one item at a time.**
