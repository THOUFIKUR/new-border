# BorderPulse — Handoff Document for Next AI Agent

> This document is for the NEXT AI agent taking over this project.
> It contains everything needed to understand the exact current state.

---

## ⚠️ CRITICAL: This is a continuation, NOT a new project

Do NOT:
- Recreate the project from scratch
- Delete or overwrite existing files
- Create duplicate backends, frontends, or Supabase projects
- Reset Supabase schema or storage buckets

---

## Current System State (Verified 2026-08-23)

### Everything Working:
| Component | Status |
|-----------|--------|
| Camera | ✅ 1280×720 @ 15.1 FPS |
| YOLO11n | ✅ Loaded, detecting persons with track IDs |
| FastAPI Backend | ✅ Running on port 8000 |
| React Frontend | ✅ Running on port 5173, all 10 pages |
| Supabase | ✅ Connected and writing data |
| Storage | ✅ event-images and event-videos buckets exist |
| WebSocket stream | ✅ Live camera + detections to frontend |
| Zone Engine | ✅ Polygon + ray-casting PIP |
| Decision Engine | ✅ State machine, temporal confirmation |
| Sensor Fusion | ✅ Configurable weights |
| Event Manager | ✅ Cooldown, deduplication |
| Evidence Capture | ✅ Ring buffer, snapshot, video |
| Evidence Upload | ✅ Supabase Storage upload |
| Radar | 🟡 SIMULATED (no physical hardware yet) |
| Ground sensor | 🟡 SIMULATED (no physical hardware yet) |
| Unit tests | ✅ 24/24 PASSED |

### NOT Yet Done:
| Item | Status |
|------|--------|
| ESP32 firmware | Written but NOT FLASHED |
| ESP32 physical connection | ❌ User hasn't connected yet |
| Real buzzer test | ❌ Blocked by ESP32 connection |
| End-to-end evidence test | 🔲 Should verify snapshot + video actually saved |
| Raspberry Pi migration | 🔲 Future phase |

---

## Architecture Summary

```
backend/app.py          — FastAPI app, lifespan orchestrator, WebSocket broadcaster
backend/camera/         — Thread-based camera capture, health monitor
backend/vision/         — YOLO inference thread, zone engine, annotator
backend/decision/       — State machine per (track_id, zone_id), fusion engine
backend/sensors/        — Abstract SensorProvider + SimulatedSensorProvider
backend/events/         — EventManager, cooldown, deduplication
backend/evidence/       — RingBuffer pre-event, snapshot, post-event video, upload
backend/hardware/       — ESP32 HTTP REST client, heartbeat thread
backend/database/       — Supabase service-role client
backend/api/            — Route handlers (health, events, zones, sensors, devices, esp32, settings)

frontend/src/
  App.jsx               — React Router
  contexts/StreamContext.jsx — WebSocket auto-reconnect
  services/api.js       — All REST + WebSocket calls
  components/           — Sidebar, StatusBar, CameraFeed, ui library
  pages/                — Overview, LiveMonitor, Events, EventDetail, Zones, Sensors, 
                          Devices, CameraHealth, Analytics, Settings

esp32/firmware/borderpulse_esp32.ino  — Arduino firmware (to be flashed)
tests/test_zones.py     — 13 zone + PIP tests
tests/test_decision.py  — 11 fusion + decision + event tests
```

---

## Supabase Project

- **Project Ref:** frmisnduadstnjwyyvym
- **URL:** https://frmisnduadstnjwyyvym.supabase.co
- **Tables:** devices, cameras, zones, sensor_readings, detections, events, event_media, camera_health, system_settings
- **Storage buckets:** event-images, event-videos (PRIVATE)
- **RLS:** Enabled on all tables

---

## Key Design Decisions

1. **Camera thread is independent** — camera never blocks on YOLO, Supabase, or uploads
2. **YOLO inference in a separate thread** — uses latest-frame slot (bounded queue depth = 1)
3. **Decision state machine per (track_id, zone_id) pair** — prevents flooding
4. **10-second event cooldown** — one continuous intrusion = one event
5. **High-confidence fast path** — confidence ≥ 0.85 + in zone = immediate ALARM, no temporal delay
6. **ESP32 failure is non-fatal** — vision, zones, events, Supabase all continue if ESP32 is offline
7. **Fusion weights are configurable** — Settings page sliders, persisted to Supabase system_settings table
8. **Radar + ground are SIMULATED** — clearly labeled in UI, toggle-able from Sensors page

---

## Next Actions for the Agent

**Priority 1 (User must do, not agent):**
1. User identifies exact ESP32 board variant
2. User wires buzzer to GPIO25 + GND (see HARDWARE_SETUP.md)
3. User sets WIFI credentials in esp32/firmware/borderpulse_esp32.ino
4. User flashes firmware using Arduino IDE
5. User updates ESP32_IP in .env with actual IP from Serial Monitor

**Priority 2 (Agent can do):**
1. Verify end-to-end evidence capture: trigger test event → check d:\hackelite\evidence\
2. Verify Supabase Storage upload: check event_media table for public URLs
3. Once ESP32 is online: test full alarm workflow

**Priority 3 (Future):**
1. Wire and integrate real radar sensor
2. Wire and integrate real ground vibration sensor
3. Switch SENSOR_SIMULATION=false in .env
4. Run Raspberry Pi migration when hardware available

---

## How to Start the System

```powershell
# Terminal 1 — Backend
cd d:\hackelite
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend  
cd d:\hackelite\frontend
npm run dev

# Open browser:
# http://localhost:5173/
```

---

## Files NOT to Touch

These files contain working code and should NOT be overwritten without a specific reason:

- `backend/app.py` — orchestration logic is delicate
- `backend/vision/zones.py` — tested ray-casting PIP
- `backend/decision/engine.py` — state machine logic
- `backend/decision/fusion.py` — weighted fusion
- `backend/events/manager.py` — cooldown + dedup logic
- `backend/camera/capture.py` — thread-safe camera capture
- `tests/test_zones.py` — 13 passing tests
- `tests/test_decision.py` — 11 passing tests
- `frontend/src/contexts/StreamContext.jsx` — auto-reconnect WS

---

## What the User Told the Agent

> "I did not connect the ESP32 and I don't know how to connect it, what pins for the sensor and buzzer, and how to connect to the software. The AI credits are over so I have to continue with a new account. Give me the full overview like how to test, how the overflow of the ESP32 and sensor connection works, and how to connect to the software."

**This has been addressed by:**
- `ESP32_SETUP.md` — step-by-step flashing + connection guide
- `HARDWARE_SETUP.md` — complete wiring diagrams
- `TESTING.md` — full test procedures including end-to-end workflow
- `PROJECT_STATE.md` — current verified state
- `SOFTWARE_SETUP.md` — software installation + startup
