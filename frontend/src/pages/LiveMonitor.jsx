// BorderPulse — 02 LIVE MONITOR (SOC Command Center Style)
import { useStream } from '../contexts/StreamContext';
import CameraFeed from '../components/CameraFeed';
import { useState } from 'react';
import { setSimulation, testEvent } from '../services/api';

export default function LiveMonitor() {
  const { streamData } = useStream();
  const [viewMode, setViewMode]   = useState('SINGLE'); // 'SINGLE' | 'DUAL' | 'FULLSCREEN'
  const [activeCam, setActiveCam] = useState('cam-01'); // 'cam-01' | 'cam-02'

  const detections      = streamData?.detections ?? [];
  const sensors         = streamData?.sensor_state ?? {};
  const decision        = streamData?.decision_state ?? 'MONITORING';
  const esp32           = streamData?.esp32_status ?? {};
  const fps             = streamData?.camera_status?.fps ?? 0;
  const latency         = streamData?.inference_latency_ms ?? 0;
  const temporalStates  = streamData?.temporal_states ?? [];
  const buzzerActive    = streamData?.buzzer_active ?? false;
  const cameras         = streamData?.cameras ?? {};

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

  const isCritical = decision.includes('CRITICAL') || decision.includes('ALARM') || decision.includes('CONFIRMED');
  const isWarning  = decision.includes('PROBABLE') || decision.includes('POSSIBLE');
  const ground     = sensors?.ground ?? {};

  return (
    <div className="flex-1 overflow-hidden flex flex-col p-4 gap-3 bg-bp-bg font-mono text-bp-text">
      {/* Top Header Bar & View Selectors */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-bp-border">
        <div>
          <h1 className="text-lg font-bold text-bp-green tracking-wider uppercase font-sans">02 LIVE MONITOR</h1>
          <p className="text-xs text-bp-muted">REAL-TIME YOLO26n DETECTION, MULTI-CAMERA STREAM & GROUND SENSE</p>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Controls */}
          <div className="flex items-center bg-bp-surface border border-bp-border rounded p-0.5 text-xs">
            <button
              onClick={() => setViewMode('SINGLE')}
              className={`px-3 py-1 rounded font-bold transition-all ${
                viewMode === 'SINGLE' ? 'bg-bp-green/20 text-bp-green border border-bp-green/40' : 'text-bp-dim hover:text-bp-text'
              }`}
            >
              SINGLE VIEW
            </button>
            <button
              onClick={() => setViewMode('DUAL')}
              className={`px-3 py-1 rounded font-bold transition-all ${
                viewMode === 'DUAL' ? 'bg-bp-green/20 text-bp-green border border-bp-green/40' : 'text-bp-dim hover:text-bp-text'
              }`}
            >
              DUAL VIEW
            </button>
            <button
              onClick={() => setViewMode('FULLSCREEN')}
              className={`px-3 py-1 rounded font-bold transition-all ${
                viewMode === 'FULLSCREEN' ? 'bg-bp-green/20 text-bp-green border border-bp-green/40' : 'text-bp-dim hover:text-bp-text'
              }`}
            >
              FULLSCREEN
            </button>
          </div>

          {/* Camera Selector (in Single Mode) */}
          {viewMode === 'SINGLE' && (
            <div className="flex items-center bg-bp-surface border border-bp-border rounded p-0.5 text-xs">
              <button
                onClick={() => setActiveCam('cam-01')}
                className={`px-2.5 py-1 rounded font-bold ${
                  activeCam === 'cam-01' ? 'bg-bp-accent/20 text-bp-accent border border-bp-accent/40' : 'text-bp-dim'
                }`}
              >
                CAM-01
              </button>
              <button
                onClick={() => setActiveCam('cam-02')}
                className={`px-2.5 py-1 rounded font-bold ${
                  activeCam === 'cam-02' ? 'bg-bp-accent/20 text-bp-accent border border-bp-accent/40' : 'text-bp-dim'
                }`}
              >
                CAM-02
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="flex-1 grid grid-cols-1 xl:grid-cols-4 gap-4 min-h-0">
        {/* Camera Feed Container */}
        <div className={`flex flex-col gap-3 min-h-0 ${viewMode === 'FULLSCREEN' ? 'xl:col-span-4' : 'xl:col-span-3'}`}>
          {/* Dual Camera Layout */}
          {viewMode === 'DUAL' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1 min-h-0">
              <div className="bg-bp-surface border border-bp-border rounded p-2 flex flex-col">
                <div className="text-xs font-bold text-bp-green mb-1 flex justify-between">
                  <span>CAM-01 (PRIMARY LAPTOP)</span>
                  <span className="text-bp-dim">{fps.toFixed(1)} FPS</span>
                </div>
                <CameraFeed camId="cam_01" className="flex-1 min-h-0 aspect-video" />
              </div>
              <div className="bg-bp-surface border border-bp-border rounded p-2 flex flex-col">
                <div className="text-xs font-bold text-bp-accent mb-1 flex justify-between">
                  <span>CAM-02 (SECONDARY ANGLE)</span>
                  <span className="text-bp-green">LIVE</span>
                </div>
                <CameraFeed camId="cam_02" className="flex-1 min-h-0 aspect-video" />
              </div>
            </div>
          ) : (
            /* Single Camera Layout */
            <div className="bg-bp-surface border border-bp-border rounded p-2 flex-1 flex flex-col min-h-0 relative">
              <div className="flex justify-between items-center px-2 py-1 mb-1 border-b border-bp-border text-xs">
                <span className="text-bp-green font-bold flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-bp-green animate-pulse" />
                  {activeCam === 'cam-01' ? 'CAM-01 (PRIMARY LAPTOP CAM)' : 'CAM-02 (SECONDARY ANGLE)'}
                </span>
                <span className="text-bp-dim">MODEL: YOLO26n | {fps.toFixed(1)} FPS | {latency.toFixed(0)} MS</span>
              </div>
              <CameraFeed camId={activeCam === 'cam-01' ? 'cam_01' : 'cam_02'} className="flex-1 min-h-0 aspect-video" />
            </div>
          )}

          {/* Real Telemetry Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
            <div className="bg-bp-surface border border-bp-border rounded px-3 py-1.5 flex justify-between items-center">
              <span className="text-bp-dim">FPS</span>
              <span className="text-bp-green font-bold">{fps.toFixed(1)}</span>
            </div>
            <div className="bg-bp-surface border border-bp-border rounded px-3 py-1.5 flex justify-between items-center">
              <span className="text-bp-dim">LATENCY</span>
              <span className="text-bp-accent font-bold">{latency.toFixed(0)} ms</span>
            </div>
            <div className="bg-bp-surface border border-bp-border rounded px-3 py-1.5 flex justify-between items-center">
              <span className="text-bp-dim">OBJECTS</span>
              <span className="text-bp-text font-bold">{detections.length}</span>
            </div>
            <div className="bg-bp-surface border border-bp-border rounded px-3 py-1.5 flex justify-between items-center">
              <span className="text-bp-dim">ESP32</span>
              <span className={esp32.online ? 'text-bp-green font-bold' : 'text-bp-warning font-bold'}>
                {esp32.online ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            <div className="bg-bp-surface border border-bp-border rounded px-3 py-1.5 flex justify-between items-center col-span-2 sm:col-span-1">
              <span className="text-bp-dim">BUZZER</span>
              <span className={buzzerActive ? 'text-bp-danger font-bold animate-pulse' : 'text-bp-dim'}>
                {buzzerActive ? 'ACTIVE' : 'SILENT'}
              </span>
            </div>
          </div>
        </div>

        {/* Right Telemetry Column (Hidden in Fullscreen Mode) */}
        {viewMode !== 'FULLSCREEN' && (
          <div className="space-y-3 overflow-y-auto">
            {/* Decision Engine Status Card */}
            <div className={`p-3 bg-bp-surface border rounded ${isCritical ? 'border-bp-danger bg-bp-danger/10 shadow-[0_0_12px_rgba(255,42,42,0.2)]' : isWarning ? 'border-bp-warning bg-bp-warning/10' : 'border-bp-border'}`}>
              <div className="text-[10px] text-bp-muted uppercase tracking-wider">DECISION ENGINE STATE</div>
              <div className={`text-sm font-bold mt-1 ${isCritical ? 'text-bp-danger animate-pulse' : isWarning ? 'text-bp-warning' : 'text-bp-green'}`}>
                {decision || 'MONITORING'}
              </div>
              {buzzerActive && (
                <div className="mt-2 pt-2 border-t border-bp-danger/30 text-xs font-bold text-bp-danger flex items-center gap-1.5">
                  <span className="animate-pulse">🔔</span> ESP32 GPIO25 BUZZER ON
                </div>
              )}
            </div>

            {/* Person Temporal Confirmation Progress */}
            <div className="p-3 bg-bp-surface border border-bp-border rounded space-y-2">
              <div className="text-xs font-bold text-bp-green uppercase border-b border-bp-border pb-1">
                TEMPORAL CONFIRMATION (4 FRAMES)
              </div>
              {temporalStates.length === 0 ? (
                <div className="text-xs text-bp-muted py-2 text-center">NO ACTIVE PERSON TRACKS</div>
              ) : (
                temporalStates.map((s, idx) => {
                  const count = s.person_confirm_count || 0;
                  const req = s.person_confirm_required || 4;
                  const isAlarm = s.state?.includes('ALARM') || s.state?.includes('ACTIVE');
                  return (
                    <div key={idx} className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-bp-dim">TRACK #{s.track_id ?? '01'} ({s.class_name || 'person'})</span>
                        <span className={isAlarm ? 'text-bp-danger font-bold' : 'text-bp-warning font-bold'}>
                          {count}/{req} {isAlarm && '✓'}
                        </span>
                      </div>
                      <div className="w-full bg-bp-bg h-1.5 rounded overflow-hidden border border-bp-border">
                        <div
                          className={`h-full transition-all duration-300 ${isAlarm ? 'bg-bp-danger' : 'bg-bp-warning'}`}
                          style={{ width: `${Math.min(100, (count / req) * 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Ground Sensor GPIO26 Details */}
            <div className="p-3 bg-bp-surface border border-bp-border rounded space-y-1.5 text-xs">
              <div className="text-xs font-bold text-bp-accent uppercase border-b border-bp-border pb-1">
                GROUND SENSOR (GPIO26 REAL)
              </div>
              <div className="flex justify-between">
                <span className="text-bp-dim">STATUS</span>
                <span className={ground.triggered ? 'text-bp-danger font-bold' : 'text-bp-green font-bold'}>
                  {ground.triggered ? 'TRIGGERED YES (RAW=1)' : 'CLEAR (RAW=0)'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-bp-dim">MODE</span>
                <span className="text-bp-accent">{ground.mode || 'REAL'}</span>
              </div>
            </div>

            {/* Simulation Controls */}
            <div className="p-3 bg-bp-surface border border-bp-border rounded space-y-2 text-xs">
              <div className="text-xs font-bold text-bp-warning uppercase border-b border-bp-border pb-1">
                SIMULATION OVERRIDES
              </div>
              <div className="flex justify-between items-center">
                <span className="text-bp-dim">Ground Override</span>
                <button
                  onClick={toggleGround}
                  className={`px-2.5 py-0.5 rounded text-[11px] font-bold border ${simGround ? 'bg-bp-warning/20 border-bp-warning text-bp-warning' : 'bg-bp-bg border-bp-border text-bp-muted'}`}
                >
                  {simGround ? 'SIM ON' : 'SIM OFF'}
                </button>
              </div>
            </div>

            <button
              onClick={testEvent}
              className="w-full py-2 bg-bp-warning/20 border border-bp-warning text-bp-warning font-bold text-xs rounded hover:bg-bp-warning/30"
            >
              ⚡ TRIGGER TEST EVENT
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
