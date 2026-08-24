import sys, os
sys.stdout.reconfigure(encoding='utf-8')

base = 'evidence_local'
for d in [base, base+'/snapshots', base+'/videos']:
    exists = os.path.exists(d)
    count = len(os.listdir(d)) if exists else 0
    print(f'{d}: exists={exists} files={count}')

pages = ['Overview.jsx','LiveMonitor.jsx','Events.jsx','EventDetail.jsx',
         'Zones.jsx','Sensors.jsx','Devices.jsx','CameraHealth.jsx',
         'Analytics.jsx','Settings.jsx']
for p in pages:
    path = f'frontend/src/pages/{p}'
    size = os.path.getsize(path) if os.path.exists(path) else 0
    status = 'EXISTS' if size > 0 else 'MISSING'
    print(f'Page {p}: {status} ({size} bytes)')

# Check backend components
components = [
    'backend/app.py','backend/config.py',
    'backend/camera/capture.py','backend/camera/health_monitor.py',
    'backend/vision/detector.py','backend/vision/zones.py',
    'backend/decision/engine.py','backend/decision/fusion.py',
    'backend/sensors/provider.py','backend/events/manager.py',
    'backend/evidence/capture.py','backend/evidence/storage.py',
    'backend/hardware/esp32.py','backend/database/supabase_client.py',
]
print('\nBackend components:')
for c in components:
    sz = os.path.getsize(c) if os.path.exists(c) else 0
    status = 'PASS' if sz > 100 else 'FAIL'
    print(f'  [{status}] {c} ({sz} bytes)')
