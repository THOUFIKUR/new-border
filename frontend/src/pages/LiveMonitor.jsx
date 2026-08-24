// BorderPulse — Live Monitor Page (full detection + zone + sensor fusion panel)
import { useStream } from '../contexts/StreamContext';
import CameraFeed from '../components/CameraFeed';
import { Card, SectionHeader, ConfBar, Btn } from '../components/ui';
import { setSimulation, testEvent } from '../services/api';
import { useState } from 'react';

function SensorPanel({ sensors }) {
  const radar  = sensors?.radar  ?? {};
  const ground = sensors?.ground ?? {};

  return (
    <Card>
      <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Sensor Evidence</div>
      {[
        { label: 'VISION',   mode: 'REAL',      color: 'text-bp-accent' },
        { label: 'RADAR',    mode: radar.mode,  triggered: radar.triggered,  sim: true },
        { label: 'GROUND',   mode: ground.mode, triggered: ground.triggered, sim: true },
        { label: 'TEMPORAL', mode: 'ENGINE',    color: 'text-bp-dim' },
      ].map(({ label, mode, triggered, sim, color }) => (
        <div key={label} className="flex items-center justify-between py-2 border-b border-bp-border last:border-0">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-mono font-bold ${color || (triggered ? 'text-red-300' : 'text-bp-muted')}`}>{label}</span>
            {sim && <span className="text-xs text-yellow-600/60 border border-yellow-700/40 px-1 rounded">SIM</span>}
          </div>
          <span className={`text-xs px-2 py-0.5 rounded font-semibold ${triggered ? 'bg-red-900/40 text-red-300' : 'bg-black/40 text-bp-muted'}`}>
            {triggered === undefined ? mode?.toUpperCase() : triggered ? 'ACTIVE' : 'CLEAR'}
          </span>
        </div>
      ))}
    </Card>
  );
}

function DetectionList({ detections }) {
  if (!detections || detections.length === 0) {
    return (
      <Card>
        <div className="text-xs text-bp-muted uppercase tracking-widest mb-2">Detections</div>
        <div className="text-bp-muted text-sm py-4 text-center">No detections in current frame</div>
      </Card>
    );
  }
  return (
    <Card>
      <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">
        Detections ({detections.length})
      </div>
      <div className="space-y-2 max-h-52 overflow-y-auto">
        {detections.map((d, i) => (
          <div key={i} className="bg-black/30 rounded px-3 py-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-semibold text-bp-text capitalize">{d.class_name}</span>
              {d.track_id != null && (
                <span className="text-xs text-bp-muted mono">#{d.track_id}</span>
              )}
            </div>
            <div className="mt-1.5">
              <ConfBar value={d.confidence} />
            </div>
            <div className="text-xs text-bp-muted mt-1">{(d.confidence * 100).toFixed(1)}% confidence</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function LiveMonitor() {
  const { streamData } = useStream();
  const detections   = streamData?.detections ?? [];
  const sensors      = streamData?.sensor_state ?? {};
  const decision     = streamData?.decision_state ?? 'MONITORING';
  const esp32        = streamData?.esp32_status ?? {};
  const fps          = streamData?.camera_status?.fps ?? 0;
  const latency      = streamData?.inference_latency_ms ?? 0;

  const [simRadar,  setSimRadar]  = useState(false);
  const [simGround, setSimGround] = useState(false);

  const toggleRadar = async () => {
    const next = !simRadar;
    setSimRadar(next);
    await setSimulation(next, simGround).catch(() => {});
  };
  const toggleGround = async () => {
    const next = !simGround;
    setSimGround(next);
    await setSimulation(simRadar, next).catch(() => {});
  };

  const isCritical = decision.includes('CRITICAL');
  const isWarning  = decision.includes('CONFIRMED') || decision.includes('PROBABLE');

  return (
    <div className="flex-1 overflow-hidden flex flex-col p-4 gap-4 bg-grid">
      <SectionHeader title="Live Monitor" subtitle="Real-time detection and zone enforcement" />

      <div className="flex-1 grid grid-cols-1 xl:grid-cols-4 gap-4 min-h-0">
        {/* Camera feed — large */}
        <div className="xl:col-span-3 flex flex-col gap-3 min-h-0">
          <CameraFeed className="flex-1 min-h-0" />

          {/* Diagnostics bar */}
          <div className="flex gap-2 flex-wrap">
            {[
              { label: 'FPS',      value: fps.toFixed(1),    unit: 'fps'  },
              { label: 'LATENCY',  value: latency.toFixed(0), unit: 'ms'  },
              { label: 'OBJECTS',  value: detections.length,  unit: 'det' },
              { label: 'ESP32',    value: esp32.online ? 'ONLINE' : 'OFFLINE', danger: !esp32.online },
            ].map(({ label, value, unit, danger }) => (
              <div key={label} className="flex items-center gap-2 bg-bp-card border border-bp-border rounded px-3 py-1.5">
                <span className="text-xs text-bp-muted">{label}</span>
                <span className={`text-xs font-semibold mono ${danger ? 'text-bp-danger' : 'text-bp-accent'}`}>
                  {value}{unit && <span className="text-bp-dim ml-0.5">{unit}</span>}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel */}
        <div className="space-y-3 overflow-y-auto">
          {/* Decision state */}
          <Card className={`border ${isCritical ? 'border-red-500 alert-critical' : isWarning ? 'border-yellow-500' : 'border-bp-border'}`}>
            <div className="text-xs text-bp-muted uppercase tracking-widest mb-2">Decision State</div>
            <div className={`text-base font-bold ${isCritical ? 'text-red-300' : isWarning ? 'text-yellow-300' : 'text-bp-safe'}`}>
              {decision || 'MONITORING'}
            </div>
          </Card>

          <SensorPanel sensors={sensors} />
          <DetectionList detections={detections} />

          {/* Simulation controls */}
          <Card>
            <div className="text-xs text-yellow-600 uppercase tracking-widest mb-3">Simulation Controls</div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-bp-dim">Radar — SIMULATED</span>
                <button
                  onClick={toggleRadar}
                  className={`w-10 h-5 rounded-full transition-colors relative ${simRadar ? 'bg-bp-accent' : 'bg-bp-border'}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${simRadar ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-bp-dim">Ground — SIMULATED</span>
                <button
                  onClick={toggleGround}
                  className={`w-10 h-5 rounded-full transition-colors relative ${simGround ? 'bg-bp-accent' : 'bg-bp-border'}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${simGround ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
            </div>
            <div className="mt-2 text-xs text-yellow-600/60">These are simulated values — not real sensors</div>
          </Card>

          {/* Test event */}
          <Btn onClick={testEvent} variant="warning" size="sm" className="w-full justify-center">
            ⚡ Trigger Test Event
          </Btn>
        </div>
      </div>
    </div>
  );
}
