// BorderPulse — Live Monitor Page
// Shows real-time detection, zone enforcement, temporal confirmation progress,
// sensor evidence panel, and ESP32 buzzer status.
import { useStream } from '../contexts/StreamContext';
import CameraFeed from '../components/CameraFeed';
import { Card, SectionHeader, ConfBar, Btn } from '../components/ui';
import { setSimulation, testEvent } from '../services/api';
import { useState } from 'react';

// ─── Temporal Confirmation Progress ──────────────────────────────────────

function TemporalConfirmation({ temporalStates, buzzerActive }) {
  const personTracks = (temporalStates || []).filter(
    s => s.class_name === 'person' && s.state !== 'NO_DETECTION'
  );

  if (personTracks.length === 0 && !buzzerActive) return null;

  return (
    <Card>
      <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Temporal Confirmation</div>
      {buzzerActive && (
        <div className="mb-3 px-3 py-2 bg-red-900/40 border border-red-500/60 rounded text-sm font-bold text-red-300 flex items-center gap-2 animate-pulse">
          <span className="text-lg">🔔</span> ESP32 BUZZER ACTIVE
        </div>
      )}
      {personTracks.length === 0 && (
        <div className="text-xs text-bp-muted">No active person tracks</div>
      )}
      {personTracks.map((s, i) => {
        const count = s.person_confirm_count || 0;
        const required = s.person_confirm_required || 4;
        const ratio = Math.min(1, count / required);
        const isAlarm = s.state === 'ALARM_ACTIVE' || s.state === 'EVIDENCE_CAPTURE' || s.state === 'EVENT_ACTIVE';
        const isBuilding = s.state === 'POSSIBLE_DETECTION' || s.state === 'TEMPORAL_CONFIRMATION';

        return (
          <div key={i} className="mb-3 last:mb-0">
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-xs text-bp-dim font-mono">
                PERSON TRACK #{s.track_id ?? '—'}
              </span>
              <span className={`text-xs font-bold mono ${
                isAlarm ? 'text-red-400' : isBuilding ? 'text-yellow-400' : 'text-bp-muted'
              }`}>
                {isAlarm ? 'CONFIRMED ✓' : `${count} / ${required}`}
              </span>
            </div>
            {/* Progress bar */}
            <div className="h-2 bg-bp-border rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  isAlarm ? 'bg-red-500' : 'bg-yellow-400'
                }`}
                style={{ width: `${ratio * 100}%` }}
              />
            </div>
            {isAlarm && (
              <div className="mt-1 text-xs text-red-400 font-semibold">
                CONFIRMED HUMAN INTRUSION
              </div>
            )}
          </div>
        );
      })}
    </Card>
  );
}

// ─── Sensor Panel ─────────────────────────────────────────────────────────

function SensorPanel({ sensors }) {
  const radar  = sensors?.radar  ?? {};
  const ground = sensors?.ground ?? {};

  const items = [
    {
      label: 'VISION',
      mode: 'REAL',
      triggered: undefined,
      color: 'text-bp-accent',
      badge: null,
    },
    {
      label: 'RADAR',
      mode: radar.mode || 'SIMULATED',
      triggered: radar.triggered,
      color: null,
      badge: 'SIM',
      badgeColor: 'text-yellow-600/70 border-yellow-700/40',
    },
    {
      label: 'GROUND',
      mode: ground.mode || 'SIMULATED',
      triggered: ground.triggered,
      color: null,
      // REAL if ESP32 online, SIMULATED otherwise
      badge: ground.mode === 'REAL' ? 'REAL' : 'SIM',
      badgeColor: ground.mode === 'REAL'
        ? 'text-green-400 border-green-600/40'
        : 'text-yellow-600/70 border-yellow-700/40',
    },
    {
      label: 'TEMPORAL',
      mode: 'ENGINE',
      triggered: undefined,
      color: 'text-bp-dim',
      badge: null,
    },
  ];

  return (
    <Card>
      <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Sensor Evidence</div>
      {items.map(({ label, mode, triggered, color, badge, badgeColor }) => (
        <div key={label} className="flex items-center justify-between py-2 border-b border-bp-border last:border-0">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-mono font-bold ${color || (triggered ? 'text-red-300' : 'text-bp-muted')}`}>
              {label}
            </span>
            {badge && (
              <span className={`text-xs border px-1 rounded ${badgeColor}`}>{badge}</span>
            )}
          </div>
          <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
            triggered ? 'bg-red-900/40 text-red-300' : 'bg-black/40 text-bp-muted'
          }`}>
            {triggered === undefined
              ? mode?.toUpperCase()
              : triggered ? 'ACTIVE' : 'CLEAR'}
          </span>
        </div>
      ))}
    </Card>
  );
}

// ─── Detection List ───────────────────────────────────────────────────────

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

// ─── Main Page ────────────────────────────────────────────────────────────

export default function LiveMonitor() {
  const { streamData } = useStream();
  const detections      = streamData?.detections ?? [];
  const sensors         = streamData?.sensor_state ?? {};
  const decision        = streamData?.decision_state ?? 'MONITORING';
  const esp32           = streamData?.esp32_status ?? {};
  const fps             = streamData?.camera_status?.fps ?? 0;
  const latency         = streamData?.inference_latency_ms ?? 0;
  const temporalStates  = streamData?.temporal_states ?? [];
  const buzzerActive    = streamData?.buzzer_active ?? false;

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

  const isCritical = decision.includes('CRITICAL') || decision.includes('CONFIRMED');
  const isWarning  = decision.includes('PROBABLE') || decision.includes('POSSIBLE');

  return (
    <div className="flex-1 overflow-hidden flex flex-col p-4 gap-4 bg-grid">
      <SectionHeader title="Live Monitor" subtitle="Real-time detection and zone enforcement" />

      <div className="flex-1 grid grid-cols-1 xl:grid-cols-4 gap-4 min-h-0">
        {/* Camera feed */}
        <div className="xl:col-span-3 flex flex-col gap-3 min-h-0">
          <CameraFeed className="flex-1 min-h-0" />

          {/* Diagnostics bar */}
          <div className="flex gap-2 flex-wrap">
            {[
              { label: 'FPS',     value: fps.toFixed(1),     unit: 'fps' },
              { label: 'LATENCY', value: latency.toFixed(0), unit: 'ms' },
              { label: 'OBJECTS', value: detections.length,  unit: 'det' },
              { label: 'ESP32',   value: esp32.online ? 'ONLINE' : 'OFFLINE', danger: !esp32.online },
              { label: 'BUZZER',  value: buzzerActive ? 'ACTIVE' : 'SILENT', danger: buzzerActive },
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

          <TemporalConfirmation temporalStates={temporalStates} buzzerActive={buzzerActive} />
          <SensorPanel sensors={sensors} />
          <DetectionList detections={detections} />

          {/* Simulation controls */}
          <Card>
            <div className="text-xs text-yellow-600 uppercase tracking-widest mb-3">Simulation Controls</div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm text-bp-dim">Radar</span>
                  <span className="ml-1.5 text-xs text-yellow-600/70 border border-yellow-700/40 px-1 rounded">SIMULATED</span>
                </div>
                <button
                  onClick={toggleRadar}
                  className={`w-10 h-5 rounded-full transition-colors relative ${simRadar ? 'bg-bp-accent' : 'bg-bp-border'}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${simRadar ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm text-bp-dim">Ground</span>
                  <span className="ml-1.5 text-xs text-yellow-600/70 border border-yellow-700/40 px-1 rounded">SIM</span>
                  <span className="ml-1 text-xs text-bp-muted">(real via ESP32)</span>
                </div>
                <button
                  onClick={toggleGround}
                  className={`w-10 h-5 rounded-full transition-colors relative ${simGround ? 'bg-bp-accent' : 'bg-bp-border'}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${simGround ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
            </div>
            <div className="mt-2 text-xs text-yellow-600/60">Radar = simulated. Ground = real via ESP32 GPIO26 when online.</div>
          </Card>

          <Btn onClick={testEvent} variant="warning" size="sm" className="w-full justify-center">
            ⚡ Trigger Test Event
          </Btn>
        </div>
      </div>
    </div>
  );
}
