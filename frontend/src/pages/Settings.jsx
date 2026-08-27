// BorderPulse — 05 SYSTEM CONFIGURATION & LIVE TELEMETRY
import { useEffect, useState } from 'react';
import { useStream } from '../contexts/StreamContext';
import { getSettings, updateDecision } from '../services/api';

export default function Settings() {
  const { streamData } = useStream();
  const [loading, setLoading] = useState(true);
  const [saved,   setSaved]   = useState(false);

  // Config parameters
  const [highConf,  setHighConf]  = useState(0.85);
  const [minFrames, setMinFrames] = useState(4);
  const [cooldown,  setCooldown]  = useState(10.0);

  const [settingsData, setSettingsData] = useState(null);

  useEffect(() => {
    getSettings()
      .then(d => {
        setSettingsData(d);
        setHighConf(d.decision?.human_high_confidence ?? 0.85);
        setMinFrames(d.decision?.min_frames ?? 4);
        setCooldown(d.decision?.cooldown_seconds ?? 10.0);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const saveConfig = async () => {
    try {
      await updateDecision({
        min_frames: minFrames,
        window_seconds: 1.0,
        cooldown_seconds: cooldown,
        human_high_confidence: highConf,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      console.error('Save config error:', e);
    }
  };

  const cam    = streamData?.camera_status ?? {};
  const esp32  = streamData?.esp32_status ?? {};
  const ground = streamData?.sensor_state?.ground ?? {};

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-bp-text bg-bp-bg">
      <div className="pb-2 border-b border-bp-border">
        <h1 className="text-lg font-bold text-bp-green tracking-wider uppercase font-sans">05 SYSTEM CONFIGURATION</h1>
        <p className="text-xs text-bp-muted">MANAGED SYSTEM PARAMETERS & LIVE HARDWARE TELEMETRY</p>
      </div>

      {saved && (
        <div className="p-3 bg-bp-green/10 border border-bp-green text-bp-green rounded text-xs font-bold">
          ✓ SYSTEM CONFIGURATION UPDATED SUCCESSFULLY
        </div>
      )}

      {/* Configuration Parameters Card */}
      <div className="p-4 bg-bp-surface border border-bp-border rounded space-y-4">
        <div className="text-xs font-bold text-bp-green uppercase tracking-wider border-b border-bp-border pb-1">
          CONFIGURABLE PARAMETERS
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs text-bp-dim">YOLO HIGH-CONFIDENCE OVERRIDE</label>
            <input
              type="number" step="0.01" min="0.5" max="1.0"
              value={highConf}
              onChange={e => setHighConf(parseFloat(e.target.value))}
              className="w-full bg-bp-bg border border-bp-border rounded px-3 py-1.5 text-xs text-bp-green font-bold"
            />
            <div className="text-[10px] text-bp-muted">Default: 0.85. Detections ≥ this threshold bypass temporal confirmation.</div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-bp-dim">PERSON TEMPORAL CONFIRMATION FRAMES</label>
            <input
              type="number" step="1" min="1" max="10"
              value={minFrames}
              onChange={e => setMinFrames(parseInt(e.target.value))}
              className="w-full bg-bp-bg border border-bp-border rounded px-3 py-1.5 text-xs text-bp-accent font-bold"
            />
            <div className="text-[10px] text-bp-muted">Default: 4 frames. Consecutive in-zone frames required to confirm intrusion.</div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-bp-dim">EVENT COOLDOWN PERIOD (SECONDS)</label>
            <input
              type="number" step="1" min="1" max="60"
              value={cooldown}
              onChange={e => setCooldown(parseFloat(e.target.value))}
              className="w-full bg-bp-bg border border-bp-border rounded px-3 py-1.5 text-xs text-bp-text font-bold"
            />
            <div className="text-[10px] text-bp-muted">Default: 10.0 seconds. Cooldown interval before re-triggering new event.</div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-bp-dim">GROUND SENSOR MAX ALARM DURATION</label>
            <input
              type="text" disabled value="5.0 SECONDS (GROUND_MAX_ALARM_SECONDS)"
              className="w-full bg-bp-bg border border-bp-border rounded px-3 py-1.5 text-xs text-bp-dim font-bold"
            />
            <div className="text-[10px] text-bp-muted">Default: 5.0 seconds cap for ground-only alarms.</div>
          </div>
        </div>

        <button
          onClick={saveConfig}
          className="px-4 py-2 bg-bp-green text-black font-bold text-xs rounded hover:bg-bp-green/90 shadow-[0_0_10px_rgba(0,255,102,0.2)]"
        >
          SAVE SYSTEM CONFIGURATION
        </button>
      </div>

      {/* Live Hardware Telemetry Panel */}
      <div className="p-4 bg-bp-surface border border-bp-border rounded space-y-3">
        <div className="text-xs font-bold text-bp-accent uppercase tracking-wider border-b border-bp-border pb-1">
          LIVE HARDWARE TELEMETRY & SPECS (READ-ONLY)
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
          <div className="p-3 bg-bp-bg border border-bp-border rounded space-y-1">
            <div className="text-bp-muted text-[10px]">DETECTION MODEL</div>
            <div className="text-bp-green font-bold text-sm">YOLO26n</div>
            <div className="text-bp-dim text-[10px]">models/yolo/yolo26n.pt</div>
          </div>

          <div className="p-3 bg-bp-bg border border-bp-border rounded space-y-1">
            <div className="text-bp-muted text-[10px]">GROUND SENSOR HARDWARE</div>
            <div className="text-bp-accent font-bold text-sm">GPIO 26 (REAL)</div>
            <div className="text-bp-dim text-[10px]">ESP32 DIGITAL INPUT</div>
          </div>

          <div className="p-3 bg-bp-bg border border-bp-border rounded space-y-1">
            <div className="text-bp-muted text-[10px]">PHYSICAL BUZZER HARDWARE</div>
            <div className="text-bp-danger font-bold text-sm">GPIO 25 (BUZZER)</div>
            <div className="text-bp-dim text-[10px]">ONE-SHOT TRANSITION CONTROL</div>
          </div>

          <div className="p-3 bg-bp-bg border border-bp-border rounded space-y-1">
            <div className="text-bp-muted text-[10px]">PRIMARY CAMERA (CAM-01)</div>
            <div className="text-bp-text font-bold text-sm">{cam.resolution || '1280x720'}</div>
            <div className="text-bp-dim text-[10px]">{cam.fps?.toFixed(1) || '0.0'} FPS</div>
          </div>

          <div className="p-3 bg-bp-bg border border-bp-border rounded space-y-1">
            <div className="text-bp-muted text-[10px]">ESP32 TARGET IP</div>
            <div className="text-bp-text font-bold text-sm">{esp32.ip || '192.168.137.201'}</div>
            <div className="text-bp-dim text-[10px]">{esp32.online ? 'STATUS: ONLINE (HTTP 200)' : 'STATUS: OFFLINE'}</div>
          </div>

          <div className="p-3 bg-bp-bg border border-bp-border rounded space-y-1">
            <div className="text-bp-muted text-[10px]">RADAR SENSOR</div>
            <div className="text-bp-warning font-bold text-sm">PROTOTYPE SIM</div>
            <div className="text-bp-dim text-[10px]">BINARY INPUT OVERRIDE</div>
          </div>
        </div>
      </div>
    </div>
  );
}
