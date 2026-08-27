// BorderPulse — API + WebSocket service layer
const envBackend = import.meta.env.VITE_BACKEND_URL;
export const BASE = envBackend ? envBackend.replace(/\/$/, '') : 'http://localhost:8000';

const defaultWs = BASE.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
export const WS_BASE = import.meta.env.VITE_WS_URL ? import.meta.env.VITE_WS_URL.replace(/\/$/, '') : defaultWs;

async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json();
}

// Health
export const getHealth = () => apiFetch('/api/health');

// Events
export const getEvents = (params = '') => apiFetch(`/api/events${params}`);
export const getEvent  = (id) => apiFetch(`/api/events/${id}`);
export const updateEvent = (id, action) =>
  apiFetch(`/api/events/${id}`, { method: 'PATCH', body: JSON.stringify({ action }) });
export const getEventMedia = (id) => apiFetch(`/api/events/${id}/media`);

// Zones
export const getZones    = () => apiFetch('/api/zones');
export const createZone  = (data) => apiFetch('/api/zones', { method: 'POST', body: JSON.stringify(data) });
export const updateZone  = (id, data) => apiFetch(`/api/zones/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteZone  = (id) => apiFetch(`/api/zones/${id}`, { method: 'DELETE' });
export const enableZone  = (id) => apiFetch(`/api/zones/${id}/enable`, { method: 'POST' });
export const disableZone = (id) => apiFetch(`/api/zones/${id}/disable`, { method: 'POST' });

// Sensors
export const getSensorState  = () => apiFetch('/api/sensors/state');
export const setSimulation   = (radar, ground) =>
  apiFetch('/api/sensors/simulate', { method: 'POST', body: JSON.stringify({ radar, ground }) });

// Devices
export const getDevices = () => apiFetch('/api/devices');
export const getCameras = () => apiFetch('/api/cameras');
export const sendCameraFrame = (base64Image, cameraId = 'cam_01') =>
  apiFetch('/api/camera/frame', {
    method: 'POST',
    body: JSON.stringify({ image: base64Image, camera_id: cameraId }),
  });

// ESP32
export const getEsp32Status = () => apiFetch('/api/esp32/status');
export const triggerAlarm   = (reason = 'test', ms = 3000) =>
  apiFetch('/api/esp32/alarm', { method: 'POST', body: JSON.stringify({ active: true, reason, duration_ms: ms }) });
export const stopAlarm      = () =>
  apiFetch('/api/esp32/alarm', { method: 'POST', body: JSON.stringify({ active: false }) });
export const testBuzzer     = () => apiFetch('/api/esp32/test/buzzer', { method: 'POST' });

// Settings
export const getSettings     = () => apiFetch('/api/settings');
export const updateFusion    = (data) => apiFetch('/api/settings/fusion', { method: 'PUT', body: JSON.stringify(data) });
export const updateDecision  = (data) => apiFetch('/api/settings/decision', { method: 'PUT', body: JSON.stringify(data) });

// Analytics
export const getAnalytics = () => apiFetch('/api/analytics/summary');
export const getCameraHealth = () => apiFetch('/api/camera/health');

// Tests
export const testEvent   = () => apiFetch('/api/test/event', { method: 'POST' });
export const testBuzzerApi = () => apiFetch('/api/test/buzzer', { method: 'POST' });

// WebSocket stream
export function createStreamSocket(onMessage, onClose) {
  const ws = new WebSocket(`${WS_BASE}/ws/stream`);
  ws.onopen  = () => { console.log('[WS] Connected'); ws.send('ping'); };
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  ws.onclose = () => { console.log('[WS] Disconnected'); onClose?.(); };
  ws.onerror = (e) => console.error('[WS] Error', e);
  // Keepalive ping
  const ping = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.send('ping');
  }, 10000);
  return { ws, disconnect: () => { clearInterval(ping); ws.close(); } };
}
