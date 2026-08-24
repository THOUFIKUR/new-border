# BorderPulse — README

> AI Multi-Sensor Restricted-Area Security, Intrusion Detection and Edge-AI Monitoring System

---

## What Is BorderPulse?

BorderPulse is a real-time AI security system that uses a laptop or Raspberry Pi camera combined with YOLO object detection, a configurable restricted-zone engine, and optional physical sensors (radar + ground vibration) to detect intrusions, trigger alarms on an ESP32 buzzer, and log all events to Supabase with snapshot and video evidence.

```
CAMERA → YOLO → OBJECT TRACKING → RESTRICTED POLYGON
→ TEMPORAL CONFIRMATION → SENSOR FUSION → DECISION ENGINE
→ EVENT ENGINE → ESP32 BUZZER → SUPABASE → DASHBOARD
```

---

## Quick Start

### Prerequisites
- Windows 10/11 or Raspberry Pi OS
- Python 3.10+
- Node.js 20+
- Git

### 1. Set up environment

```powershell
cd d:\hackelite
copy .env.example .env
# Edit .env — fill in SUPABASE_SERVICE_ROLE_KEY from Supabase Dashboard → Settings → API
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Start backend

```powershell
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### 4. Start frontend (new terminal)

```powershell
cd frontend
npm install
npm run dev
```

### 5. Open dashboard

```
http://localhost:5173/
```

---

## System Architecture

| Layer | Technology |
|-------|-----------|
| Camera capture | OpenCV, dedicated thread |
| Object detection | YOLO11n (Ultralytics) |
| Object tracking | ByteTrack (built into Ultralytics) |
| Zone engine | Ray-casting point-in-polygon |
| Decision engine | State machine + temporal confirmation |
| Sensor fusion | Configurable weighted evidence |
| Backend API | FastAPI + WebSocket |
| Database | Supabase (PostgreSQL) |
| Storage | Supabase Storage (event-images, event-videos) |
| Frontend | React + Vite + TailwindCSS |
| Edge hardware | ESP32 (Wi-Fi HTTP REST) |

---

## Pages

| Page | URL | Purpose |
|------|-----|---------|
| Overview | `/` | System status dashboard |
| Live Monitor | `/monitor` | Camera feed + detection panel |
| Events | `/events` | Security event log |
| Event Detail | `/events/:id` | Evidence, fusion data, actions |
| Zones | `/zones` | Interactive polygon zone editor |
| Sensors | `/sensors` | Sensor state + simulation controls |
| Devices | `/devices` | Camera + ESP32 hardware status |
| Camera Health | `/health` | Image quality metrics |
| Analytics | `/analytics` | Event statistics + charts |
| Settings | `/settings` | Fusion weights + decision config |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Full system health check |
| GET | `/api/events` | List events |
| PATCH | `/api/events/{id}` | Acknowledge/resolve/false-positive |
| GET | `/api/zones` | List zones |
| POST | `/api/zones` | Create zone |
| PUT | `/api/zones/{id}` | Update zone |
| DELETE | `/api/zones/{id}` | Delete zone |
| GET | `/api/sensors/state` | Current sensor state |
| POST | `/api/sensors/simulate` | Set simulated sensor values |
| GET | `/api/esp32/status` | ESP32 connection status |
| POST | `/api/esp32/alarm` | Trigger/stop buzzer |
| POST | `/api/esp32/test/buzzer` | Test buzzer |
| GET | `/api/settings` | All configurable settings |
| PUT | `/api/settings/fusion` | Update fusion weights |
| PUT | `/api/settings/decision` | Update decision engine config |
| GET | `/api/analytics/summary` | Event statistics |
| GET | `/api/camera/health` | Camera image quality |
| POST | `/api/test/event` | Create synthetic test event |
| WS | `/ws/stream` | Live camera + detection stream |

---

## Hardware (Optional)

See `HARDWARE_SETUP.md` for full wiring instructions.

| Component | Purpose |
|-----------|---------|
| ESP32 | Wi-Fi controller + buzzer driver |
| Active buzzer | Audio alarm on intrusion |
| Radar module (future) | Motion presence evidence |
| Ground sensor (future) | Vibration disturbance evidence |

> **Radar and ground sensor are currently SIMULATED in software.**  
> The system clearly labels simulated values throughout the UI.

---

## Environment Variables

See `.env.example` for all variables. Key ones:

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | **Backend only** — never expose to frontend |
| `SUPABASE_PUBLISHABLE_KEY` | Anon key for frontend |
| `ESP32_IP` | IP address of your ESP32 on Wi-Fi |
| `CAMERA_INDEX` | OpenCV camera index (usually 0) |
| `YOLO_MODEL` | Path to YOLO model file |
| `SENSOR_SIMULATION` | true = simulated sensors |

---

## Tests

```powershell
python -m pytest tests/ -v
# Expected: 24/24 PASSED
```

See `TESTING.md` for full end-to-end test procedures.
