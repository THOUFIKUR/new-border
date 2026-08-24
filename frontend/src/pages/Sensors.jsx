// BorderPulse — Sensors Page
import { useEffect, useState } from 'react';
import { useStream } from '../contexts/StreamContext';
import { getSensorState, setSimulation } from '../services/api';
import { Card, SectionHeader, SimulatedBadge } from '../components/ui';

export default function Sensors() {
  const { streamData } = useStream();
  const [simRadar,  setSimRadar]  = useState(false);
  const [simGround, setSimGround] = useState(false);
  const [loading,   setLoading]   = useState(false);

  const sensors = streamData?.sensor_state;
  const radar   = sensors?.radar  ?? {};
  const ground  = sensors?.ground ?? {};

  const toggle = async (type, val) => {
    setLoading(true);
    const r = type === 'radar'  ? val : simRadar;
    const g = type === 'ground' ? val : simGround;
    if (type === 'radar')  setSimRadar(val);
    if (type === 'ground') setSimGround(val);
    try {
      await setSimulation(r, g);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <SectionHeader
        title="Sensor Panel"
        subtitle="Real-time sensor state. Radar and ground are currently simulated."
      />

      {/* Simulation warning */}
      <div className="bg-yellow-900/20 border border-yellow-700/40 rounded-lg p-4 text-yellow-400 text-sm">
        <div className="font-semibold mb-1">⚠ Sensor Simulation Active</div>
        Radar and ground sensors are software-simulated. When real hardware is wired and verified,
        the backend will switch to REAL mode automatically. The UI will reflect the hardware mode.
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Vision */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold text-bp-text">Vision (YOLO)</div>
            <SimulatedBadge mode="REAL" />
          </div>
          <div className="text-xs text-bp-muted mb-2">Live camera object detection — always real</div>
          <div className="flex items-center gap-2">
            <span className={`status-dot ${streamData?.detections?.length > 0 ? 'dot-online' : 'dot-simulated'}`} />
            <span className="text-sm">
              {streamData?.detections?.length ?? 0} detection(s) in current frame
            </span>
          </div>
        </Card>

        {/* Radar */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold text-bp-text">Radar Sensor</div>
            <SimulatedBadge mode={radar.mode || 'SIMULATED'} />
          </div>
          <div className={`text-2xl font-bold mb-3 ${radar.triggered ? 'text-red-400' : 'text-bp-safe'}`}>
            {radar.triggered ? 'TRIGGERED' : 'CLEAR'}
          </div>
          <div className="text-xs text-bp-muted mb-4">
            Provides motion/presence evidence only. Not a human classifier.
          </div>
          {/* Simulation toggle */}
          <div className="flex items-center justify-between p-3 bg-black/30 rounded border border-bp-border">
            <span className="text-sm text-bp-dim">Simulate Trigger</span>
            <button
              onClick={() => toggle('radar', !simRadar)}
              disabled={loading}
              className={`w-11 h-6 rounded-full transition-colors relative ${simRadar ? 'bg-red-500' : 'bg-bp-border'}`}
            >
              <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${simRadar ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>
          <div className="text-xs text-yellow-600/60 mt-2">Physical wiring NOT YET CONFIGURED</div>
        </Card>

        {/* Ground */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold text-bp-text">Ground Vibration Sensor</div>
            <SimulatedBadge mode={ground.mode || 'SIMULATED'} />
          </div>
          <div className={`text-2xl font-bold mb-3 ${ground.triggered ? 'text-red-400' : 'text-bp-safe'}`}>
            {ground.triggered ? 'TRIGGERED' : 'CLEAR'}
          </div>
          <div className="text-xs text-bp-muted mb-4">
            Provides physical disturbance evidence only. Not a human/animal classifier.
          </div>
          <div className="flex items-center justify-between p-3 bg-black/30 rounded border border-bp-border">
            <span className="text-sm text-bp-dim">Simulate Trigger</span>
            <button
              onClick={() => toggle('ground', !simGround)}
              disabled={loading}
              className={`w-11 h-6 rounded-full transition-colors relative ${simGround ? 'bg-red-500' : 'bg-bp-border'}`}
            >
              <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${simGround ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>
          <div className="text-xs text-yellow-600/60 mt-2">Physical wiring NOT YET CONFIGURED</div>
        </Card>

        {/* Temporal */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold text-bp-text">Temporal Confirmation</div>
            <span className="text-xs border border-bp-border text-bp-muted px-1.5 py-0.5 rounded">ENGINE</span>
          </div>
          <div className="text-xs text-bp-muted">
            Software-computed from consecutive frame detections within a time window.
            Default: 3 frames in 1 second.
          </div>
          <div className="mt-3 space-y-1.5 text-xs text-bp-dim">
            <div>• Not a physical sensor</div>
            <div>• Configurable in Settings → Decision Engine</div>
            <div>• High-confidence detections (≥0.85) skip temporal delay</div>
          </div>
        </Card>
      </div>

      {/* Fusion weights display */}
      <Card>
        <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Current Fusion Weights</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Vision',   weight: 0.55, color: 'bg-bp-accent' },
            { label: 'Radar',    weight: 0.20, color: 'bg-yellow-500' },
            { label: 'Ground',   weight: 0.15, color: 'bg-orange-500' },
            { label: 'Temporal', weight: 0.10, color: 'bg-purple-500' },
          ].map(({ label, weight, color }) => (
            <div key={label} className="bg-black/30 rounded p-3 border border-bp-border">
              <div className="text-xs text-bp-muted mb-2">{label}</div>
              <div className="text-xl font-bold mono text-bp-text">{(weight * 100).toFixed(0)}%</div>
              <div className="h-1.5 bg-bp-border rounded-full mt-2">
                <div className={`h-full rounded-full ${color}`} style={{ width: `${weight * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
        <div className="text-xs text-bp-muted mt-3">
          Configurable in Settings. These are engineering starting values — not scientifically validated.
        </div>
      </Card>
    </div>
  );
}
