# BorderPulse — Software Setup Guide

---

## Prerequisites

| Software | Required Version | Check Command |
|----------|-----------------|---------------|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Node.js | 20+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |
| Arduino IDE | 2.x (for ESP32 only) | Download from arduino.cc |

---

## Step 1 — Clone / Open Workspace

```powershell
# Already cloned:
cd d:\hackelite
```

---

## Step 2 — Configure Environment Variables

```powershell
# Copy the example file
copy .env.example .env

# Open .env in Notepad or VS Code and fill in:
notepad .env
```

### Required .env values:

```dotenv
# Supabase — get from: https://app.supabase.com → Your Project → Settings → API
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJh...YOUR_SERVICE_ROLE_KEY...   ← KEEP SECRET, backend only
SUPABASE_PUBLISHABLE_KEY=eyJh...YOUR_ANON_KEY...             ← Safe for frontend

# ESP32 — set after flashing firmware (see ESP32_SETUP.md)
ESP32_IP=192.168.1.100     ← Change this to your actual ESP32 IP
ESP32_PORT=80

# Camera
CAMERA_INDEX=0             ← Try 0 first; change to 1 or 2 if wrong camera opens

# YOLO
YOLO_MODEL=models/yolo/yolo11n.pt

# Simulation (keep true until real sensors are wired)
SENSOR_SIMULATION=true
```

### Where to get Supabase keys:
1. Go to https://app.supabase.com
2. Click your project (frmisnduadstnjwyyvym)
3. Left sidebar → **Settings** → **API**
4. Copy:
   - "Project URL" → `SUPABASE_URL`
   - "service_role" secret key → `SUPABASE_SERVICE_ROLE_KEY`
   - "anon" public key → `SUPABASE_PUBLISHABLE_KEY`

---

## Step 3 — Install Python Dependencies

```powershell
cd d:\hackelite
pip install -r requirements.txt
```

### Key dependencies:
```
ultralytics     — YOLO + ByteTrack
opencv-python   — Camera capture
fastapi         — REST API
uvicorn         — ASGI server
websockets      — WebSocket support
httpx           — ESP32 HTTP client
supabase        — Supabase client
python-dotenv   — .env loading
pillow          — Image processing
```

### If YOLO model is missing:
The backend downloads it automatically on first start. Or manually:
```powershell
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
# Then move it:
mkdir models\yolo
move yolo11n.pt models\yolo\yolo11n.pt
```

---

## Step 4 — Install Frontend Dependencies

```powershell
cd d:\hackelite\frontend
npm install
```

---

## Step 5 — Start the System

### Option A: Two separate terminals (Recommended)

**Terminal 1 — Backend:**
```powershell
cd d:\hackelite
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Watch for:
```
CAMERA    ✓  1280x720
YOLO      ✓
SUPABASE  ✓
ESP32     OFFLINE  (normal if not connected)
RADAR     SIMULATED
GROUND    SIMULATED
Application startup complete.
```

**Terminal 2 — Frontend:**
```powershell
cd d:\hackelite\frontend
npm run dev
```

Watch for:
```
VITE v8.x.x  ready in 2000 ms
➜  Local:   http://localhost:5173/
```

### Option B: Start script (create this file)

```powershell
# start_borderpulse.ps1
Start-Process powershell -ArgumentList "-NoExit -Command cd d:\hackelite; python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit -Command cd d:\hackelite\frontend; npm run dev"
Start-Sleep 5
Start-Process "http://localhost:5173/"
```

---

## Step 6 — Open Dashboard

Open your browser and go to:
```
http://localhost:5173/
```

Verify you see:
- ✅ Dark security operations dashboard
- ✅ Sidebar navigation
- ✅ Camera feed (Overview and Live Monitor pages)
- ✅ Green "BACKEND LIVE" indicator in sidebar
- ✅ "CAMERA ONLINE" in status bar

---

## Common Setup Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `No module named uvicorn` | pip install failed | `pip install uvicorn` |
| `No module named ultralytics` | pip install failed | `pip install ultralytics` |
| `Camera OFFLINE` | Wrong CAMERA_INDEX | Change `CAMERA_INDEX=1` in .env |
| `SUPABASE error` | Wrong key | Check SUPABASE_SERVICE_ROLE_KEY in .env |
| `Port 8000 already in use` | Another process | `netstat -ano | findstr :8000` then kill the PID |
| `CORS error in browser` | Frontend URL not in CORS | Already configured for `localhost:5173` |
| Frontend shows blank page | Tailwind not compiled | `npm install` and restart `npm run dev` |
| `TypeError: Router.__init__()` | Starlette version conflict | `pip install fastapi>=0.115.0 starlette>=0.41.0` |

---

## File Structure

```
d:\hackelite\
├── .env                  ← Your secrets (DO NOT commit)
├── .env.example          ← Template (safe to commit)
├── requirements.txt      ← Python dependencies
├── README.md
├── PROJECT_STATE.md
├── ESP32_SETUP.md
├── HARDWARE_SETUP.md
├── SOFTWARE_SETUP.md     ← This file
├── TESTING.md
├── TROUBLESHOOTING.md
│
├── backend\
│   ├── app.py            ← FastAPI main
│   ├── config.py         ← All env/config
│   ├── camera\           ← Camera capture + health
│   ├── vision\           ← YOLO, zones, annotator
│   ├── decision\         ← State machine, fusion
│   ├── sensors\          ← Sensor provider (sim/real)
│   ├── events\           ← Event creation, cooldown
│   ├── evidence\         ← Ring buffer, video, upload
│   ├── hardware\         ← ESP32 HTTP client
│   ├── database\         ← Supabase client
│   └── api\              ← Route handlers
│
├── frontend\
│   ├── src\
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css
│   │   ├── components\   ← Sidebar, CameraFeed, StatusBar, ui
│   │   ├── contexts\     ← WebSocket StreamContext
│   │   ├── pages\        ← All 10 pages
│   │   └── services\     ← api.js
│   └── tailwind.config.js
│
├── esp32\
│   └── firmware\
│       └── borderpulse_esp32.ino  ← Flash this to ESP32
│
├── models\
│   └── yolo\
│       └── yolo11n.pt    ← Auto-downloaded on first start
│
├── evidence\             ← Local snapshots + videos
│   ├── snapshots\
│   └── videos\
│
└── tests\
    ├── test_zones.py     ← 13 tests
    └── test_decision.py  ← 11 tests
```
