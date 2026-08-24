// BorderPulse — Settings Page
import { useEffect, useState } from 'react';
import { getSettings, updateFusion, updateDecision } from '../services/api';
import { Card, SectionHeader, Btn, Spinner } from '../components/ui';

function SliderRow({ label, value, min, max, step, onChange, note }) {
  return (
    <div className="py-2">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-bp-text">{label}</span>
        <span className="mono text-sm text-bp-accent">{value}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full accent-blue-400 h-1.5 bg-bp-border rounded"
      />
      {note && <div className="text-xs text-bp-muted mt-0.5">{note}</div>}
    </div>
  );
}

function NumRow({ label, value, min, max, step, onChange, note }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-bp-border last:border-0">
      <div>
        <div className="text-sm text-bp-text">{label}</div>
        {note && <div className="text-xs text-bp-muted">{note}</div>}
      </div>
      <input
        type="number" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-20 bg-bp-card border border-bp-border rounded px-2 py-1 text-sm mono text-bp-accent text-right"
      />
    </div>
  );
}

export default function Settings() {
  const [loading, setLoading] = useState(true);
  const [saved,   setSaved]   = useState(false);

  // Fusion
  const [wVision,   setWVision]   = useState(0.55);
  const [wRadar,    setWRadar]    = useState(0.20);
  const [wGround,   setWGround]   = useState(0.15);
  const [wTemporal, setWTemporal] = useState(0.10);
  const [threshold, setThreshold] = useState(0.65);

  // Decision
  const [minFrames,  setMinFrames]  = useState(3);
  const [windowSecs, setWindowSecs] = useState(1.0);
  const [cooldown,   setCooldown]   = useState(10.0);
  const [highConf,   setHighConf]   = useState(0.85);

  // Read-only info
  const [info, setInfo] = useState(null);

  useEffect(() => {
    getSettings().then(d => {
      setWVision(d.fusion?.w_vision   ?? 0.55);
      setWRadar(d.fusion?.w_radar     ?? 0.20);
      setWGround(d.fusion?.w_ground   ?? 0.15);
      setWTemporal(d.fusion?.w_temporal ?? 0.10);
      setThreshold(d.fusion?.confirmed_threshold ?? 0.65);
      setMinFrames(d.decision?.min_frames ?? 3);
      setWindowSecs(d.decision?.window_seconds ?? 1.0);
      setCooldown(d.decision?.cooldown_seconds ?? 10.0);
      setHighConf(d.decision?.human_high_confidence ?? 0.85);
      setInfo(d);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  const weightSum = (wVision + wRadar + wGround + wTemporal).toFixed(2);
  const weightOk  = Math.abs(parseFloat(weightSum) - 1.0) < 0.02;

  const saveFusion = async () => {
    await updateFusion({ vision: wVision, radar: wRadar, ground: wGround, temporal: wTemporal, confirmed_threshold: threshold });
    setSaved(true); setTimeout(() => setSaved(false), 2000);
  };

  const saveDecision = async () => {
    await updateDecision({ min_frames: minFrames, window_seconds: windowSecs, cooldown_seconds: cooldown, human_high_confidence: highConf });
    setSaved(true); setTimeout(() => setSaved(false), 2000);
  };

  if (loading) return <div className="p-4"><Spinner /></div>;

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <SectionHeader title="Settings" subtitle="Fusion weights, decision engine, and system configuration" />

      {saved && (
        <div className="bg-green-900/30 border border-green-700/50 text-green-300 text-sm rounded px-4 py-2">
          ✓ Settings saved successfully
        </div>
      )}

      {/* Sensor Fusion Weights */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm font-semibold text-bp-text">Sensor Fusion Weights</div>
            <div className="text-xs text-bp-muted">Engineering starting values — calibrate with real operational data</div>
          </div>
          <div className={`text-xs mono px-2 py-1 rounded border ${weightOk ? 'border-green-600 text-green-400' : 'border-red-600 text-red-400'}`}>
            Sum: {weightSum} {weightOk ? '✓' : '≠ 1.0'}
          </div>
        </div>

        <SliderRow label="Vision (YOLO)"      value={wVision}   min={0} max={1} step={0.01} onChange={setWVision}   note="Primary detection source — real camera data" />
        <SliderRow label="Radar (SIMULATED)"  value={wRadar}    min={0} max={1} step={0.01} onChange={setWRadar}    note="Motion evidence only — not a human classifier" />
        <SliderRow label="Ground (SIMULATED)" value={wGround}   min={0} max={1} step={0.01} onChange={setWGround}   note="Physical disturbance — not a classifier" />
        <SliderRow label="Temporal"           value={wTemporal} min={0} max={1} step={0.01} onChange={setWTemporal} note="Frame-count confirmation within time window" />
        <SliderRow label="Confirmed Threshold" value={threshold} min={0.1} max={1} step={0.01} onChange={setThreshold} note="Fused score above this → CONFIRMED state" />

        <Btn variant="primary" onClick={saveFusion} className="mt-3">Save Fusion Weights</Btn>
      </Card>

      {/* Decision Engine */}
      <Card>
        <div className="mb-4">
          <div className="text-sm font-semibold text-bp-text">Decision Engine</div>
          <div className="text-xs text-bp-muted">Temporal confirmation and alarm thresholds</div>
        </div>

        <NumRow label="Min Frames"             value={minFrames}  min={1} max={30}  step={1}    onChange={setMinFrames}  note="Min consecutive frames in window to confirm" />
        <NumRow label="Window (seconds)"       value={windowSecs} min={0.1} max={10} step={0.1} onChange={setWindowSecs} note="Time window for frame counting" />
        <NumRow label="Event Cooldown (s)"     value={cooldown}   min={1} max={120} step={1}    onChange={setCooldown}   note="Min seconds between events per track+zone" />
        <NumRow label="High-Confidence (>=)" value={highConf}   min={0.5} max={1} step={0.01} onChange={setHighConf}   note="Persons at this confidence skip temporal delay" />

        <Btn variant="primary" onClick={saveDecision} className="mt-3">Save Decision Config</Btn>
      </Card>

      {/* Read-only system info */}
      {info && (
        <Card>
          <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">System Info (Read Only)</div>
          <div className="grid grid-cols-2 gap-x-8 text-xs">
            {[
              ['YOLO Model',      info.yolo?.model],
              ['Confidence',      `${((info.yolo?.confidence || 0)*100).toFixed(0)}%`],
              ['Image Size',      `${info.yolo?.imgsz}px`],
              ['Pre-Event Buf',   `${info.capture?.pre_event_seconds}s`],
              ['Post-Event Rec',  `${info.capture?.post_event_seconds}s`],
              ['Stream FPS',      info.stream?.fps],
              ['Runtime Mode',    info.runtime?.mode?.toUpperCase()],
              ['Sensor Sim',      info.runtime?.sensor_simulation ? 'ENABLED' : 'DISABLED'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1.5 border-b border-bp-border last:border-0">
                <span className="text-bp-muted">{k}</span>
                <span className="mono text-bp-dim">{v ?? '—'}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
