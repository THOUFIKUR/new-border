// BorderPulse — System Status Header Bar (SOC Command Center Style)
import { useState, useEffect } from 'react';
import { useStream } from '../contexts/StreamContext';

export default function StatusBar() {
  const { streamData, connected } = useStream();
  const [timeStr, setTimeStr] = useState('');
  const [utcStr, setUtcStr]   = useState('');

  useEffect(() => {
    const update = () => {
      const d = new Date();
      setTimeStr(d.toLocaleTimeString('en-US', { hour12: false }));
      setUtcStr(`UTC ${d.toISOString().slice(11, 16)}`);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  const cam     = streamData?.camera_status;
  const esp32   = streamData?.esp32_status;
  const active  = streamData?.active_events ?? [];
  const buzzer  = streamData?.buzzer_active;
  const ground  = streamData?.sensor_state?.ground;

  return (
    <header className="h-11 bg-bp-surface border-b border-bp-border flex items-center justify-between px-4 shrink-0 font-mono text-xs select-none">
      {/* Left: Branding & Status */}
      <div className="flex items-center gap-3">
        <span className="text-bp-green font-bold tracking-widest text-[11px]">BORDERPULSE</span>
        <span className="text-bp-border">|</span>
        <span className="text-bp-dim text-[10px] hidden md:inline uppercase tracking-wider">
          AUTONOMOUS BORDER INTELLIGENCE
        </span>
      </div>

      {/* Center: System Alert State */}
      <div className="flex items-center gap-2">
        {buzzer ? (
          <div className="px-2.5 py-0.5 rounded bg-bp-danger/20 border border-bp-danger text-bp-danger font-bold text-[11px] animate-pulse flex items-center gap-1.5 shadow-[0_0_10px_rgba(255,42,42,0.3)]">
            <span className="w-2 h-2 rounded-full bg-bp-danger shadow-[0_0_6px_#FF2A2A]" />
            ALARM ACTIVE ({streamData?.decision_state || 'ALERT'})
          </div>
        ) : active.length > 0 ? (
          <div className="px-2 py-0.5 rounded bg-bp-warning/20 border border-bp-warning text-bp-warning font-bold text-[11px] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-bp-warning" />
            {active.length} EVENT{active.length > 1 ? 'S' : ''} DETECTED
          </div>
        ) : (
          <div className="px-2 py-0.5 rounded bg-bp-green/10 border border-bp-green/30 text-bp-green text-[11px] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-bp-green shadow-[0_0_6px_#00FF66]" />
            SYSTEM NOMINAL
          </div>
        )}
      </div>

      {/* Right: Telemetry Indicators & Real Time */}
      <div className="flex items-center gap-3 text-[11px]">
        {/* Status dots */}
        <div className="hidden lg:flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${cam?.online ? 'bg-bp-green shadow-[0_0_4px_#00FF66]' : 'bg-bp-danger'}`} />
            <span className={cam?.online ? 'text-bp-dim' : 'text-bp-danger font-bold'}>CAM</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-bp-green shadow-[0_0_4px_#00FF66]' : 'bg-bp-danger'}`} />
            <span className={connected ? 'text-bp-dim' : 'text-bp-danger font-bold'}>BACKEND</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${esp32?.online ? 'bg-bp-green shadow-[0_0_4px_#00FF66]' : 'bg-bp-warning'}`} />
            <span className={esp32?.online ? 'text-bp-dim' : 'text-bp-warning'}>
              {esp32?.online ? 'ESP32' : 'ESP32 OFF'}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${ground?.mode === 'REAL' ? 'bg-bp-accent shadow-[0_0_4px_#00E5FF]' : 'bg-bp-warning'}`} />
            <span className="text-bp-dim">GPIO26 {ground?.mode === 'REAL' ? 'REAL' : 'SIM'}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-bp-warning" />
            <span className="text-bp-dim">RADAR SIM</span>
          </div>
        </div>

        {/* Clock */}
        <div className="border-l border-bp-border pl-3 text-[11px] text-bp-green font-bold tracking-wider">
          {timeStr} <span className="text-[10px] text-bp-muted font-normal ml-1">{utcStr}</span>
        </div>
      </div>
    </header>
  );
}
