# BorderPulse — Session 5: Three Specific Logic Changes ONLY
**Target: Antigravity, running inside D:\hackelite**

**Scope discipline: this session changes exactly three things, listed below. Do not refactor, rename, or
"clean up" anything else while in these files. Do not touch the YOLO model, the UI, Supabase, or any other
module not named here. If you notice something else that looks wrong while you're in these files, note it at
the end of your report — don't fix it now.**

---

## Change 1 — Person zone-entry trigger: any part of the body entering counts, not just the feet point

**File:** `backend/vision/zones.py`, function `check_detection()`

**Current behavior:** for `class_name == "person"`, only the bounding box's bottom-center (feet) point is
tested against the polygon (`_ray_cast_pip(px_b, py_b, zone.polygon_points)`). A person must have their feet
point specifically cross the polygon boundary before they count as "inside" — the rest of the body entering
first (e.g. approaching from the side, upper body leaning in) does not trigger anything yet.

**Wanted behavior:** as soon as **any part of the person's bounding box overlaps the restricted-zone
polygon**, treat them as inside — do not wait for the feet point specifically, and do not require the full
body to be inside.

**Implementation:** replace the single feet-point test for the `person` branch with a bounding-box-vs-polygon
overlap test. Add a helper function:

```python
def _bbox_intersects_polygon(bbox: dict, polygon: List[ZonePoint]) -> bool:
    """
    Returns True if the bounding box overlaps the polygon at all (partial entry counts).
    Approximation sufficient for this use case: true if either
      (a) any of the box's 4 corners is inside the polygon, or
      (b) any polygon vertex falls inside the box rectangle.
    This does not catch the rare case of a thin polygon edge slicing through the box
    without any corner/vertex inside it -- acceptable tradeoff for a hackathon timeline,
    note it in your report as a known limitation rather than building full edge-segment
    intersection unless there's time left at the end.
    """
    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
    if any(_ray_cast_pip(cx, cy, polygon) for cx, cy in corners):
        return True
    for v in polygon:
        if x1 <= v.x <= x2 and y1 <= v.y <= y2:
            return True
    return False
```

Then in `check_detection()`, change:
```python
if class_name == "person":
    # STRICT: feet point ONLY — audit requirement P2
    in_zone = _ray_cast_pip(px_b, py_b, zone.polygon_points)
```
to:
```python
if class_name == "person":
    in_zone = _bbox_intersects_polygon(bbox_norm, zone.polygon_points)
```

Do the same in `check_any_zone()` for consistency (it duplicates the same person-branch logic).

**Do not touch** `backend/decision/engine.py`'s temporal-confirmation or high-confidence-fast-path logic —
that stays exactly as-is. This change only affects *whether* a person counts as "inside the zone" on a given
frame, not what happens once they are.

---

## Change 2 — Alarm stays on continuously while the person remains in the zone, not just 5 seconds

**File:** `backend/hardware/esp32.py`, function `trigger_alarm()`

**Root cause (confirmed by reading the code):** `decision_engine.py` already correctly keeps the track in
`ALARM_ACTIVE` state for as long as the person remains inside the zone, and `app.py` already correctly sends
`POST /alarm/stop` the moment the person leaves (`should_stop_alarm` → `any_alarm_active` check). **The only
reason the buzzer doesn't feel continuous is the ESP32 firmware's own auto-timeout**: `trigger_alarm()`
currently defaults to `duration_ms=5000`, so the physical buzzer always cuts out after 5 seconds regardless of
whether the person is still standing in the zone, because nothing re-sends the alarm command while they wait.

**Fix — do not add a keep-alive ping loop, just change the default duration and rely on the explicit stop
call that already exists:**

In `backend/hardware/esp32.py`:
```python
def trigger_alarm(self, reason: str = "intrusion", duration_ms: int = 60000) -> bool:
```
Change `duration_ms` default from `5000` to `60000` (60 seconds). This is a safety ceiling, not the normal
off-trigger — if the backend process were to crash or hang while someone is in the zone, the buzzer will still
stop on its own after 60 seconds rather than blaring forever. The *normal* off-trigger remains the existing
`POST /alarm/stop` call in `app.py`, sent the instant `feet_inside` (per Change 1's new bbox-overlap test)
becomes false for that track. Do not change the ESP32 firmware itself — `checkAlarmTimeout()` already correctly
uses whatever `duration_ms` it's given.

Verify the call site in `backend/app.py`'s `_processing_loop()` doesn't pass an explicit shorter `duration_ms`
that would override this default — if it does, update that call site too.

Test this specifically: stand in the zone for 15+ seconds (longer than the old 5s timeout) and confirm the
buzzer stays on the whole time, then step out and confirm it stops within roughly one processing frame, not
up to 60 seconds later.

---

## Change 3 — Ground sensor triggers the alarm independently, without waiting for a YOLO person detection

**File:** `backend/app.py`, function `_processing_loop()`

**Root cause (confirmed across earlier sessions):** the fusion/decision path currently only runs *inside* the
per-YOLO-detection `for det in det_frame.detections:` loop. If the ground sensor triggers but YOLO has zero
detections in that frame (nobody visible, or camera temporarily has no person in frame), there is currently no
code path that reacts to the ground sensor at all beyond showing its raw boolean state in the UI.

**Wanted behavior:** when the ground sensor (`ground_active`, already read from real ESP32 hardware earlier in
the loop) is triggered, fire the alarm immediately — do not wait for a YOLO person detection to exist or be
confirmed in that same frame.

**Important labeling requirement, not optional:** the ground sensor only proves physical disturbance, not
human identity — this has been the consistent principle across every prior session's fusion design. Implement
the immediate trigger as a **new, independent branch** so it activates the buzzer as requested, but creates
and logs it as event type `GROUND_DISTURBANCE`, never `HUMAN_INTRUSION`. Behaviorally it does what was asked
(no waiting on YOLO); honestly, it's still labeled for what it actually is.

**Implementation sketch**, added to `_processing_loop()` as its own block that runs every tick — placed
**outside and independent of** the `if det_frame:` block, so it still executes even when there's no fresh
detection frame:

```python
# ── INDEPENDENT GROUND-SENSOR ALARM PATH (runs every tick, no YOLO dependency) ──
global _ground_alarm_active_state   # add this alongside the existing _buzzer_active_state global

if ground_active and not _ground_alarm_active_state:
    logger.info(f"[GROUND] TRIGGERED — immediate alarm, no YOLO wait, reason=GROUND_DISTURBANCE")
    _ground_alarm_active_state = True
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, esp32_client.trigger_alarm, "GROUND_DISTURBANCE")
    # apply the same decided/sent/acknowledged logging pattern used for the person path
    future.add_done_callback(lambda fut: logger.info(
        f"[GROUND_ALARM] {'ACKNOWLEDGED' if fut.result() else 'FAILED'}"
    ))
    event_manager.create_event(
        track_id=None,
        zone_id="ground-sensor",
        class_name="ground_disturbance",
        confidence=1.0,
        fused_score=1.0,
        is_critical=False,
        reason="GROUND_DISTURBANCE",
        sensor_evidence={"ground_active": True, "trigger_source": "GROUND_SENSOR_ONLY_NO_VISUAL"},
    )

elif not ground_active and _ground_alarm_active_state:
    _ground_alarm_active_state = False
    if esp32_client.status.online:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, esp32_client.stop_alarm)
    logger.info("[GROUND] CLEARED — alarm stopped")
```

Apply the same "continuous until cleared" principle as Change 2: the alarm stays on for as long as
`ground_active` remains true, and turns off as soon as it clears — not on a fixed timer.

**Known limitation to note in your report, not to fix now:** the ground sensor is a single physical device
with no per-zone mapping in the current code, so this event can't be attributed to a specific restricted zone
polygon the way a person detection can — it's a general "ground disturbance somewhere" signal. A radar/ground-
to-zone mapping was flagged as a future nice-to-have in an earlier session; don't build it now unless
everything else in this file is done and tested.

**One more thing to verify, don't change unless it's actually broken:** if a person is *also* independently
confirmed in a zone at the same time the ground sensor fires, both paths will be running concurrently
(`_buzzer_active_state` for the person path, `_ground_alarm_active_state` for this new one) — confirm they
don't fight each other over the single physical buzzer (e.g. one path's `/alarm/stop` call turning off a
buzzer the other path still wants on). If they conflict, the simplest correct fix is: the buzzer stays on as
long as *either* flag is true, and `/alarm/stop` is only sent when *both* are false.

---

## Test before reporting back

1. Walk toward the zone from the side — confirm the alarm fires as soon as any part of your body/box crosses
   the polygon line, not only when your feet cross it.
2. Stand inside the zone for 15+ seconds — confirm the buzzer stays on continuously, not just 5 seconds.
3. Step out of the zone — confirm the buzzer stops promptly.
4. Trigger the ground sensor with no one in camera view — confirm the buzzer fires immediately as
   `GROUND_DISTURBANCE`, without waiting for any YOLO detection.
5. Let the ground sensor clear — confirm the buzzer stops.
6. Report real log lines proving each of the above, not just "done."
