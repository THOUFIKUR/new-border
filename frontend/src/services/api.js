// BorderPulse — Centralized API + WebSocket service layer
// Resolves production vs local environment backend & WebSocket URLs dynamically.

const rawEnvBackend = import.meta.env.VITE_BACKEND_URL;
const rawEnvWs = import.meta.env.VITE_WS_URL;

// Helper to sanitize URLs (remove trailing slashes and spaces)
const sanitizeUrl = (url) => (url ? url.trim().replace(/\/$/, '') : '');

// Detect browser execution context
const isBrowser = typeof window !== 'undefined';
const isLocalhost =
  isBrowser &&
  (window.location.hostname === 'localhost' ||
   window.location.hostname === '127.0.0.1' ||
   window.location.hostname === '::1');

function resolveBaseUrl() {
  const envUrl = sanitizeUrl(rawEnvBackend);
  if (envUrl) {
    return envUrl;
  }

  // Local development fallback
  if (isLocalhost || !isBrowser) {
    return 'http://localhost:8000';
  }

  // Production Vercel / Cloud deployment fallback
  // NEVER use localhost:8000 on production domain when VITE_BACKEND_URL was not set at build time!
  console.warn(
    '[BorderPulse API] WARNING: VITE_BACKEND_URL environment variable is not defined in Vercel settings! ' +
    'Please add VITE_BACKEND_URL=https://<your-render-backend>.onrender.com in Vercel settings and trigger a redeploy.'
  );
  
  // Use relative root fallback so the browser does NOT attempt ERR_CONNECTION_REFUSED to localhost:8000
  return window.location.origin;
}

export const BASE = resolveBaseUrl();

function resolveWsUrl() {
  const envWs = sanitizeUrl(rawEnvWs);
  if (envWs) {
    return envWs;
  }

  // Derive WebSocket URL from BASE
  if (BASE) {
    if (BASE.startsWith('https://')) {
      return BASE.replace(/^https:\/\//, 'wss://');
    } else if (BASE.startsWith('http://')) {
      return BASE.replace(/^http:\/\//, 'ws://');
    } else if (BASE.startsWith('//')) {
      return `wss:${BASE}`;
    }
  }

  // Production fallback if BASE is relative/window.location.origin
  if (isBrowser && !isLocalhost) {
    const isHttps = window.location.protocol === 'https:';
    const wsProto = isHttps ? 'wss:' : 'ws:';
    return `${wsProto}//${window.location.host}`;
  }

  return 'ws://localhost:8000';
}

export const WS_BASE = resolveWsUrl();

console.log('[BorderPulse] API BASE URL:', BASE);
console.log('[BorderPulse] WebSocket BASE URL:', WS_BASE);

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
  ws.onopen  = () => { console.log('[WS] Connected to', WS_BASE); ws.send('ping'); };
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  ws.onclose = () => { console.log('[WS] Disconnected from', WS_BASE); onClose?.(); };
  ws.onerror = (e) => console.error('[WS] Error on', WS_BASE, e);
  // Keepalive ping
  const ping = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.send('ping');
  }, 10000);
  return { ws, disconnect: () => { clearInterval(ping); ws.close(); } };
}
