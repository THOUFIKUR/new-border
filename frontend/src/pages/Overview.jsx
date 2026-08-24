// BorderPulse — Overview Page
import { useStream } from '../contexts/StreamContext';
import { useEffect, useState } from 'react';
import CameraFeed from '../components/CameraFeed';
import { StatCard, Card, SeverityBadge, SectionHeader, StatusDot } from '../components/ui';
import { getAnalytics, getHealth } from '../services/api';

function timeAgo(ts) {
  if (!ts) return '—';
  const d = Math.floor((Date.now() / 1000) - ts);
  if (d < 60) return `${d}s ago`;
  if (d < 3600) return `${Math.floor(d/60)}m ago`;
  return `${Math.floor(d/3600)}h ago`;
}

export default function Overview() {
  const { streamData } = useStream();
  const [analytics, setAnalytics] = useState(null);
  const [health, setHealth]       = useState(null);

  useEffect(() => {
    getAnalytics().then(setAnalytics).catch(() => {});
    getHealth().then(setHealth).catch(() => {});
    const t = setInterval(() => {
      getAnalytics().then(setAnalytics).catch(() => {});
    }, 10000);
    return () => clearInterval(t);
  }, []);

  const activeEvents = streamData?.active_events ?? [];
  const cam          = streamData?.camera_status ?? {};
  const esp32        = streamData?.esp32_status ?? {};
  const sensors      = streamData?.sensor_state ?? {};
  const fps          = cam.fps ?? 0;

  const stats = [
    { label: 'Active Alerts',     value: activeEvents.length, color: activeEvents.length > 0 ? 'text-bp-danger' : 'text-bp-safe', icon: '⚡' },
    { label: 'Events Today',      value: analytics?.events_today ?? '—',    color: 'text-bp-accent', icon: '📋' },
    { label: 'Camera FPS',        value: fps > 0 ? fps.toFixed(1) : '—',   color: 'text-bp-safe',   icon: '◎', unit: 'fps' },
    { label: 'Total Events',      value: analytics?.total_events ?? '—',    color: 'text-bp-dim',    icon: '▦' },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-grid">
      <SectionHeader title="System Overview" subtitle="BorderPulse AI Intrusion Detection" />

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map(s => (
          <StatCard key={s.label} label={s.label} value={s.value} unit={s.unit} color={s.color} icon={s.icon} />
        ))}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Camera feed (wide) */}
        <div className="xl:col-span-2">
          <CameraFeed className="aspect-video" />
        </div>

        {/* Right column */}
        <div className="space-y-3">
          {/* System health */}
          <Card>
            <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">System Health</div>
            {[
              { label: 'Camera',  online: cam.online,   detail: cam.resolution },
              { label: 'Backend', online: true,          detail: `${analytics?.inference_count ?? 0} inferences` },
              { label: 'ESP32',   online: esp32.online, detail: esp32.online ? esp32.firmware_version : 'OFFLINE' },
              { label: 'Radar',   online: null,          detail: 'SIMULATED', sim: true },
              { label: 'Ground',  online: null,          detail: 'SIMULATED', sim: true },
            ].map(({ label, online, detail, sim }) => (
              <div key={label} className="flex items-center justify-between py-1.5 border-b border-bp-border last:border-0">
                <div className="flex items-center gap-2">
                  <StatusDot status={sim ? 'simulated' : online ? 'online' : 'offline'} />
                  <span className="text-sm text-bp-text">{label}</span>
                </div>
                <span className={`text-xs mono ${sim ? 'text-yellow-600' : online ? 'text-bp-dim' : 'text-bp-danger'}`}>
                  {detail || (online ? 'Online' : 'Offline')}
                </span>
              </div>
            ))}
          </Card>

          {/* Sensor state */}
          <Card>
            <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Sensor Fusion</div>
            {[
              { label: 'VISION', triggered: streamData?.detections?.some(d => d.confidence > 0.5), conf: streamData?.detections?.[0]?.confidence },
              { label: 'RADAR',  triggered: sensors?.radar?.triggered, sim: true },
              { label: 'GROUND', triggered: sensors?.ground?.triggered, sim: true },
            ].map(({ label, triggered, sim, conf }) => (
              <div key={label} className="flex items-center justify-between py-1.5">
                <span className="text-xs font-mono text-bp-muted">{label}</span>
                <div className="flex items-center gap-2">
                  {sim && <span className="text-xs text-yellow-600/60">SIM</span>}
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded ${triggered ? 'bg-red-900/40 text-red-300' : 'bg-gray-800 text-bp-muted'}`}>
                    {triggered ? 'ACTIVE' : 'CLEAR'}
                  </span>
                </div>
              </div>
            ))}
          </Card>
        </div>
      </div>

      {/* Active events */}
      {activeEvents.length > 0 && (
        <Card className="border-red-700/50">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-red-400 animate-pulse">⚡</span>
            <span className="text-sm font-semibold text-red-300">Active Alerts</span>
          </div>
          <div className="space-y-2">
            {activeEvents.map(ev => (
              <div key={ev.id} className="flex items-center justify-between bg-red-900/20 rounded px-3 py-2">
                <div>
                  <div className="text-sm font-medium text-red-200">{ev.reason}</div>
                  <div className="text-xs text-bp-muted">{ev.event_code} · {timeAgo(ev.started_at)}</div>
                </div>
                <SeverityBadge severity={ev.severity} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
