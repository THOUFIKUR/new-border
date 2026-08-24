// BorderPulse — System Status Header Bar
import { useStream } from '../contexts/StreamContext';
import { StatusDot } from './ui';

export default function StatusBar() {
  const { streamData, connected } = useStream();
  const cam    = streamData?.camera_status;
  const esp32  = streamData?.esp32_status;
  const active = streamData?.active_events ?? [];

  return (
    <header className="h-12 bg-bp-surface border-b border-bp-border flex items-center justify-between px-4 shrink-0">
      {/* Left: active alerts */}
      <div className="flex items-center gap-4">
        {active.length > 0 ? (
          <div className="flex items-center gap-2 text-red-300 text-xs font-semibold animate-pulse">
            <span className="text-red-500">⚡</span>
            {active.length} ACTIVE ALERT{active.length > 1 ? 'S' : ''}
          </div>
        ) : (
          <div className="text-bp-safe text-xs font-medium">◉ SYSTEM NOMINAL</div>
        )}
      </div>

      {/* Right: device status pills */}
      <div className="flex items-center gap-3 text-xs">
        {[
          { label: 'CAMERA', online: cam?.online },
          { label: 'BACKEND', online: connected },
          { label: 'ESP32', online: esp32?.online, offline_label: 'ESP32 OFFLINE' },
        ].map(({ label, online, offline_label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <StatusDot status={online ? 'online' : 'offline'} />
            <span className={online ? 'text-bp-dim' : 'text-bp-danger'}>
              {online ? label : (offline_label || `${label} OFFLINE`)}
            </span>
          </div>
        ))}

        <div className="border-l border-bp-border pl-3 flex items-center gap-1.5">
          <span className="status-dot dot-simulated" />
          <span className="text-yellow-600/80">RADAR SIM</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="status-dot dot-simulated" />
          <span className="text-yellow-600/80">GROUND SIM</span>
        </div>
      </div>
    </header>
  );
}
