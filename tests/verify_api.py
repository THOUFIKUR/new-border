import urllib.request, json, sys, time
sys.stdout.reconfigure(encoding='utf-8')

base = 'http://localhost:8000'

def get(path):
    try:
        r = urllib.request.urlopen(f'{base}{path}', timeout=6)
        return 200, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {'err': str(e)[:80]}

def post(path, data=None):
    try:
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(f'{base}{path}', data=body,
              headers={'Content-Type':'application/json'}, method='POST')
        r = urllib.request.urlopen(req, timeout=6)
        return 200, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {'err': str(e)[:80]}

print("=" * 60)
print("BORDERPULSE API VERIFICATION")
print("=" * 60)

# Health
code, h = get('/api/health')
cam = h.get('camera', {})
yolo = h.get('yolo', {})
supa = h.get('supabase', {})
esp = h.get('esp32', {})
print(f"\n[{code}] GET /api/health")
print(f"  camera.online   = {cam.get('online')}")
print(f"  camera.fps      = {cam.get('fps')}")
print(f"  camera.res      = {cam.get('resolution')}")
print(f"  yolo.ready      = {yolo.get('ready')}")
print(f"  yolo.model      = {yolo.get('model')}")
print(f"  supabase.ok     = {supa.get('connected')}")
print(f"  esp32.online    = {esp.get('online')}")
print(f"  esp32.error     = {esp.get('error')}")
print(f"  runtime_mode    = {h.get('runtime_mode')}")

# Events
code, d = get('/api/events')
total = d.get('total', '?')
active = d.get('active_count', '?')
print(f"\n[{code}] GET /api/events  total={total} active={active}")

# Zones
code, d = get('/api/zones')
zones = d.get('zones', [])
print(f"[{code}] GET /api/zones  count={len(zones)}")
for z in zones[:3]:
    print(f"  zone: {z.get('name')} enabled={z.get('enabled')} pts={len(z.get('polygon_points',[]))}")

# Sensors
code, d = get('/api/sensors/state')
radar = d.get('radar', {})
ground = d.get('ground', {})
print(f"[{code}] GET /api/sensors/state")
print(f"  radar.mode      = {radar.get('mode')} triggered={radar.get('triggered')}")
print(f"  ground.mode     = {ground.get('mode')} triggered={ground.get('triggered')}")

# Devices
code, d = get('/api/devices')
print(f"[{code}] GET /api/devices  count={len(d.get('devices',[]))}")

# Cameras
code, d = get('/api/cameras')
cams = d.get('cameras', [])
print(f"[{code}] GET /api/cameras  count={len(cams)}")

# ESP32
code, d = get('/api/esp32/status')
print(f"[{code}] GET /api/esp32/status  online={d.get('online')} ip={d.get('ip')}")

# Settings
code, d = get('/api/settings')
fusion = d.get('fusion', {})
decision = d.get('decision', {})
print(f"[{code}] GET /api/settings")
print(f"  w_vision={fusion.get('w_vision')} w_radar={fusion.get('w_radar')} w_ground={fusion.get('w_ground')} w_temporal={fusion.get('w_temporal')}")
print(f"  confirmed_threshold={fusion.get('confirmed_threshold')}")
print(f"  min_frames={decision.get('min_frames')} cooldown={decision.get('cooldown_seconds')} high_conf={decision.get('human_high_confidence')}")

# Analytics
code, d = get('/api/analytics/summary')
print(f"[{code}] GET /api/analytics/summary  total_events={d.get('total_events')} fps={d.get('camera_fps')}")

# Camera health
code, d = get('/api/camera/health')
ch = d.get('camera_health', {})
print(f"[{code}] GET /api/camera/health  state={ch.get('state')} brightness={ch.get('brightness_score')} blur={ch.get('blur_score')}")

# Test event
code, d = post('/api/test/event')
eid = d.get('event_id', '?')
print(f"\n[{code}] POST /api/test/event  event_id={eid}")

# Sensor simulate
code, d = post('/api/sensors/simulate', {'radar': True, 'ground': True})
print(f"[{code}] POST /api/sensors/simulate  result={d}")
# Reset
post('/api/sensors/simulate', {'radar': False, 'ground': False})

print("\n" + "=" * 60)
print("API VERIFICATION COMPLETE")
print("=" * 60)
