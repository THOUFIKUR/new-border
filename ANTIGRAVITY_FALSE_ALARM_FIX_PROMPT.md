# Antigravity Prompt — BorderPulse False-Alarm-Resilience Fix Pass

> Paste this whole file to Antigravity (or any coding agent) as the task prompt.
> Companion document: `BorderPulse_Project_Audit_Report.pdf` — read it first for the *why*
> behind each item below.

## ⚠️ This is a continuation, not a new project

Do NOT:
- Recreate the project from scratch, or regenerate files that already work.
- Reset the Supabase schema, storage buckets, or delete existing data.
- Restructure the frontend page list, routes, or component tree.
- Touch files not mentioned in this prompt unless a fix genuinely requires it — if so, explain why before doing it.

Files known to be already working and tested — do not rewrite, only make the specific
targeted edits described below where noted:
`backend/vision/zones.py`, `backend/camera/capture.py`, `tests/test_zones.py`,
`tests/test_decision.py`, `frontend/src/contexts/StreamContext.jsx`.

---

## Priority 1 — Fix the person-class alarm bypass (do this first)

**File:** `backend/decision/engine.py`, method `DecisionEngine.process()`.

**Problem:** the `if class_name == "person":` branch sets `is_critical = True` and escalates
straight to `ALARM_ACTIVE` for *any* confidence level, gated only by the cooldown timer. It
never checks `self.human_high_confidence` (0.85 by default) and never routes through the
temporal/fusion path that the `else` branch already implements for other classes. This
directly contradicts `01_MASTER_PROJECT_SPECIFICATION.pdf` Section 7, and it is the exact
failure mode ("false alarms from ambiguous person-shaped triggers") the hackathon problem
statement is about.

**Fix:**
1. Inside the `class_name == "person"` branch, only take the immediate high-confidence path
   when `confidence >= self.human_high_confidence` **and** the detection is inside the zone
   (already guaranteed by the caller in `app.py`).
2. When confidence is below that threshold, route the person detection through the *same*
   temporal-confirmation / fusion-confirmed state machine used in the `else` branch, instead
   of a separate code path. The cleanest fix is to remove the special-cased
   `if class_name == "person": is_critical = True; ...` block entirely and let all classes
   (including person) go through the existing `NO_DETECTION → POSSIBLE_DETECTION →
   TEMPORAL_CONFIRMATION → CONFIRMED → ALARM_ACTIVE` flow, with a fast-path *inside* the
   `CONFIRMED`/early states specifically for `class_name == "person" and confidence >= self.human_high_confidence`.
3. Keep `is_critical` as an output flag (used elsewhere for UI severity), but derive it from
   the actual confidence check, not just class name.
4. Do not change the temporal path's logic for non-person classes — it's correct as-is.
5. Update or add a unit test in `tests/test_decision.py` covering: (a) a low-confidence person
   detection does NOT immediately alarm, and requires temporal confirmation; (b) a
   high-confidence (>=0.85) person detection inside a zone still immediately alarms as before.
6. Run `python -m pytest tests/ -v` after — all existing 24 tests plus your new ones must pass.

---

## Priority 2 — Radar simulation toggle should actually reflect in the live stream

**File:** `backend/app.py`, inside `_processing_loop()`, the `sensor_state_dict` construction.

**Problem:** the radar entry is hardcoded:
```python
"radar": {
    "triggered": False,
    "mode": "OFFLINE",
    ...
    "label": "RADAR — NOT CONNECTED",
},
```
This ignores `sensor_state.radar_triggered` and the simulation toggle entirely, even though
`fusion_in.radar_triggered` elsewhere in the same function correctly uses
`sensor_state.radar_triggered`. The frontend's radar simulation switch on the Live Monitor
page therefore has no visible effect on the dashboard, which will look broken in a live demo
even though the backend logic is actually using it.

**Fix:** build the `radar` dict the same way the `ground` dict already is — from
`sensor_state.radar_triggered` and whether it's SIMULATED/REAL, consistent with how
`SimulatedSensorProvider` reports it.

---

## Priority 3 — False-alarm-rate metric on the Analytics page

**Files:** `backend/api/settings.py` or a new endpoint in `backend/api/events.py` for the
backend aggregation; `frontend/src/pages/Analytics.jsx` for display.

**Goal:** compute and display, e.g., `confirmed_events / total_events` and
`false_positive_events / total_events` as headline stats, pulled from the `events` table's
existing resolution field (`false_positive` / `resolved` / `acknowledged`). This directly
answers "how do you know this reduces false alarms" for a hackathon judge. Read the existing
`Analytics.jsx` file first before adding — do not duplicate existing stat cards.

---

## Priority 4 — Expose fusion score breakdown on Event Detail

**File:** `frontend/src/pages/EventDetail.jsx`.

**Goal:** the event's stored `sensor_evidence` JSON (populated from
`fusion_out.evidence` in `app.py` — contains `vision_contribution`, `radar_contribution`,
`ground_contribution`, `temporal_contribution`) should be rendered as a simple horizontal bar
breakdown per event, so an operator can see *why* each event fired. Read `EventDetail.jsx`
first to see what's already there before adding.

---

## Priority 5 — Wind-adaptive confirmation threshold (stretch goal for demo)

**Goal:** add an optional wind-speed input that raises `TEMPORAL_MIN_FRAMES` or lowers the
vision fusion weight when wind is high, mirroring the pattern described in the audit report
Section 1.2 and Section 8.2. For the hackathon demo, this does not need a real anemometer —
a manual slider on the Settings page ("Simulated wind speed") that maps to a threshold
adjustment is enough to demonstrate the concept and directly answers the "wind" part of the
problem statement wording. Wire it through `backend/decision/fusion.py`'s
`update_weights()`/config rather than hardcoding — that method already exists for exactly
this kind of runtime adjustment.

---

## Priority 6 — UI polish pass (no structural changes)

- Replace bare unicode icons (⚡ ◎ ▦ ⬡ ✓ ✗) with `lucide-react` icons of consistent size/weight
  across all pages, matching existing usage patterns already in the codebase if any.
- Normalize spacing/padding in `Card` components to a single consistent scale.
- Review the six pages not covered in the audit report's direct read-through — `Events.jsx`,
  `Sensors.jsx`, `Settings.jsx`, `CameraHealth.jsx`, `Analytics.jsx` — for layout bugs,
  placeholder text, or console errors, and fix in place without changing their structure or
  routes.
- Do not change the page list, routing, or overall dark theme — only refine within it.

---

## Priority 7 — ESP32 physical bring-up (user + agent split)

**User must do:**
1. Identify the exact ESP32 board variant (classic / S2 / S3 / C3) by physical inspection.
2. Confirm the buzzer's rated voltage (3.3V vs 5V).
3. Set real Wi-Fi credentials in `esp32/firmware/borderpulse_esp32.ino` (currently placeholder,
   lines ~31–32).
4. Flash via Arduino IDE per `ESP32_SETUP.md`.
5. Read the assigned IP from Serial Monitor (115200 baud) and set `ESP32_IP` in `.env`.

**Agent then does:**
1. `GET /api/esp32/status` → confirm `online: true`.
2. `POST /api/esp32/alarm` → confirm the buzzer physically sounds.
3. Trigger a real test intrusion end-to-end and confirm a `.jpg` and `.mp4` land in
   `evidence_local/` and are uploaded to the `event-images`/`event-videos` Supabase Storage
   buckets (check the `event_media` table for the resulting public/signed URLs).

---

## Priority 8 — Initialize git

No git repository currently exists for this project (confirmed in
`HANDOFF_FOR_NEXT_AI.md`). Run `git init`, confirm `.env` is excluded via `.gitignore`
(already present), and make an initial commit before further changes, so there's a clean
history for the hackathon submission and so future changes are reviewable/revertible.

---

## After all fixes: update PROJECT_STATE.md

Follow the existing convention in `PROJECT_STATE.md` — update the status table, the
"LAST VERIFIED TEST RESULTS" section with the new pytest output, and the "NEXT TASKS" list,
the same way previous agent passes have done. Do not delete the file's history — append/update
in place.
