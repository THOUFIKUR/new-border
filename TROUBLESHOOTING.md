# BorderPulse — Troubleshooting Guide

---

## Backend Issues

### Backend won't start: "No module named uvicorn"
```powershell
pip install uvicorn fastapi
```

### Backend won't start: "TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'"
```powershell
pip install "fastapi>=0.115.0" "starlette>=0.41.0" --upgrade
```

### Backend won't start: "Camera OFFLINE"
- Check if another app is using your camera (Teams, Zoom, etc.)
- Change `CAMERA_INDEX=1` in `.env`
- Test: `python -c "import cv2; c=cv2.VideoCapture(0); print(c.read()[0])"`

### "SUPABASE connection failed"
- Verify `SUPABASE_SERVICE_ROLE_KEY` in `.env` — must be the **service_role** key, not anon
- Key starts with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- Get it from: Supabase Dashboard → Settings → API → service_role

### Port 8000 already in use
```powershell
netstat -ano | findstr :8000
# Find the PID, then:
taskkill /PID <PID> /F
```

### "YOLO model not found"
```powershell
mkdir models\yolo
python -c "from ultralytics import YOLO; m=YOLO('yolo11n.pt'); m.save('models/yolo/yolo11n.pt')"
```

---

## Frontend Issues

### Frontend shows blank white page
- Check browser console for errors
- Run `npm install` again in `d:\hackelite\frontend\`
- Make sure `npm run dev` is running (not `npm run build`)

### "BACKEND OFFLINE" in sidebar even though backend is running
- Backend must be on port 8000
- Check `VITE_BACKEND_URL=http://localhost:8000` in `frontend/.env`
- Check Windows Firewall isn't blocking port 8000

### Camera feed not showing
- WebSocket must be connected (check sidebar for "BACKEND LIVE")
- Backend must have camera online
- Check browser console for WebSocket errors

### Tailwind styles not loading / page looks unstyled
```powershell
cd d:\hackelite\frontend
npm install
npm run dev
```

---

## ESP32 Issues

### ESP32 not appearing in COM ports
- Install the USB-to-Serial driver for your board:
  - **CP2102 chip** (most DOIT/common boards): https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
  - **CH340 chip** (some clones): https://sparks.gogo.co.nz/ch340.html
- Try a different USB cable (some cables are charge-only, no data)

### Upload fails: "Failed uploading: uploading error: exit status 2"
- Hold the **BOOT** button on the ESP32 while clicking Upload in Arduino IDE
- Release BOOT after upload starts

### ESP32 connects to Wi-Fi but backend shows "OFFLINE"
- Both ESP32 and laptop must be on the **same router**
- Update `ESP32_IP=` in `.env` with the exact IP from Serial Monitor
- Restart backend after changing .env
- Check your router's "client isolation" setting — disable it

### ESP32 connects but buzzer doesn't sound
- Check buzzer wiring (+ to GPIO25, - to GND)
- Test directly: add `digitalWrite(25, HIGH); delay(1000); digitalWrite(25, LOW);` in Arduino setup()
- Try `POST http://ESP32_IP/test/buzzer` directly in browser or Postman
- If buzzer needs 5V, use transistor circuit (see HARDWARE_SETUP.md)

### "ESP32 keeps disconnecting"
- Power issue: use a powered USB hub or a good USB cable
- Wi-Fi range: move ESP32 closer to router
- Add `WiFi.setAutoReconnect(true)` in firmware (already in borderpulse_esp32.ino)

---

## Detection / Zone Issues

### Person not being detected
- Check YOLO is loaded: `GET http://localhost:8000/api/health` → `yolo.ready: true`
- Check camera is working: `/health` page should show HEALTHY
- Person must be fully visible, not just a hand or face
- Check lighting: dark room → Camera Health page will show "DARK"

### Zone not triggering even when person is inside
- The detection point is the **bottom-center** of the bounding box
- The person's feet must be inside the polygon, not just their body
- Check zone is **enabled** (green dot on Zones page)
- Check zone has `alert_on_classes: ["person"]`

### Too many events / flooding
- Event cooldown is 10 seconds per (track_id, zone_id)
- If flooding, increase cooldown in Settings → Decision Engine → Event Cooldown

### Decision state stuck at POSSIBLE DETECTION
- Temporal confirmation requires 3 frames within 1 second
- Try moving more slowly in the zone (tracking stability)
- Or increase confidence: high-confidence ≥ 0.85 skips temporal delay entirely

---

## Supabase Issues

### Events not appearing in database
- Check backend logs for Supabase write errors
- Verify service_role key is set (not the anon key)
- Check table RLS policies in Supabase Dashboard → Authentication → Policies

### Storage upload failing
- Check `event-images` and `event-videos` buckets exist in Supabase Storage
- Check bucket is not public (should be private for security)
- Check service_role key has storage permissions

### "Duplicate table" / "relation already exists" error
- Do NOT run schema migrations again
- Tables already exist — check in Supabase Dashboard → Table Editor

---

## Performance Issues

### Camera FPS is low (< 5 FPS)
- YOLO inference is likely blocking
- Check backend: inference should run in a separate thread
- Reduce YOLO image size in `.env`: `YOLO_IMGSZ=416` (from 640)
- Close other GPU-intensive apps

### Dashboard feels slow / high latency
- Stream FPS is throttled to 5 FPS for WebSocket (this is intentional)
- Increase `STREAM_FPS=10` in `.env` if you want more frequent updates
- Check browser: Chrome usually faster than Firefox for WebSockets

### Evidence video is choppy
- This is normal for the ring buffer recording
- Pre-event buffer: 5 seconds @ stream FPS
- Post-event: 8 seconds of actual camera frames
