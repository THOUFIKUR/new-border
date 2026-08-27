// BorderPulse — 01 COMMAND CENTER
import { useStream } from '../contexts/StreamContext';
import { useEffect, useState } from 'react';
import CameraFeed from '../components/CameraFeed';
import { getAnalytics, getHealth } from '../services/api';

export default function Overview() {
  const { streamData } = useStream();
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    getAnalytics().then(setAnalytics).catch(() => {});
    const t = setInterval(() => {
      getAnalytics().then(setAnalytics).catch(() => {});
    }, 10000);
    return () => clearInterval(t);
  }, []);

  const activeEvents = streamData?.active_events ?? [];
  const cam          = streamData?.camera_status ?? {};
  const esp32        = streamData?.esp32_status ?? {};
  const sensors      = streamData?.sensor_state ?? {};
  const ground       = sensors?.ground ?? {};
  const radar        = sensors?.radar ?? {};
  const fps          = cam.fps ?? 0;
  const buzzer       = streamData?.buzzer_active;

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-bp-text bg-bp-bg">
      {/* Hero Banner Header */}
      <div className="p-4 bg-bp-surface border border-bp-border rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-full bg-gradient-to-l from-bp-green/5 to-transparent pointer-events-none" />
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-bp-green animate-pulse shadow-[0_0_8px_#00FF66]" />
            <span className="text-[11px] text-bp-green font-bold tracking-widest">COMMAND CENTER SOC — ACTIVE</span>
          </div>
          <h1 className="text-xl md:text-2xl font-black text-bp-text tracking-wider uppercase mt-1 font-sans">
            THE BORDER DOESN'T SLEEP
          </h1>
          <p className="text-xs text-bp-dim mt-0.5">
            AUTONOMOUS HUMAN INTRUSION DETECTION & REAL-TIME SENSOR FUSION
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 bg-bp-card border border-bp-border rounded text-right">
            <div className="text-[10px] text-bp-muted">DETECTION MODEL</div>
            <div className="text-xs font-bold text-bp-green">YOLO26n</div>
          </div>
          <div className="px-3 py-1.5 bg-bp-card border border-bp-border rounded text-right">
            <div className="text-[10px] text-bp-muted">GROUND SENSOR</div>
            <div className="text-xs font-bold text-bp-accent">GPIO26 REAL</div>
          </div>
        </div>
      </div>

      {/* Quick Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3 bg-bp-surface border border-bp-border rounded">
          <div className="text-[10px] text-bp-muted uppercase tracking-wider">Active Alerts</div>
          <div className={`text-xl font-bold mt-1 ${activeEvents.length > 0 ? 'text-bp-danger animate-pulse' : 'text-bp-green'}`}>
            {activeEvents.length}
          </div>
          <div className="text-[10px] text-bp-dim mt-1">{activeEvents.length > 0 ? 'CRITICAL INTRUSION' : 'NO ACTIVE THREATS'}</div>
        </div>

        <div className="p-3 bg-bp-surface border border-bp-border rounded">
          <div className="text-[10px] text-bp-muted uppercase tracking-wider">Events Today</div>
          <div className="text-xl font-bold text-bp-accent mt-1">
            {analytics?.events_today ?? 0}
          </div>
          <div className="text-[10px] text-bp-dim mt-1">TOTAL LOGGED EVENTS</div>
        </div>

        <div className="p-3 bg-bp-surface border border-bp-border rounded">
          <div className="text-[10px] text-bp-muted uppercase tracking-wider">Camera FPS</div>
          <div className="text-xl font-bold text-bp-green mt-1">
            {fps > 0 ? fps.toFixed(1) : '0.0'} <span className="text-xs text-bp-dim">FPS</span>
          </div>
          <div className="text-[10px] text-bp-dim mt-1">{cam.resolution || '1280x720'}</div>
        </div>

        <div className="p-3 bg-bp-surface border border-bp-border rounded">
          <div className="text-[10px] text-bp-muted uppercase tracking-wider">ESP32 Hardware</div>
          <div className={`text-xl font-bold mt-1 ${esp32.online ? 'text-bp-green' : 'text-bp-warning'}`}>
            {esp32.online ? 'ONLINE' : 'OFFLINE'}
          </div>
          <div className="text-[10px] text-bp-dim mt-1">{esp32.online ? 'GPIO25 BUZZER READY' : 'NO BUZZER COMM'}</div>
        </div>
      </div>

      {/* Main Grid: Camera Feed + Right Sensor Telemetry */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Camera Feed */}
        <div className="xl:col-span-2 space-y-3">
          <div className="bg-bp-surface border border-bp-border rounded p-2">
            <div className="flex justify-between items-center px-2 py-1 mb-2 border-b border-bp-border text-xs">
              <span className="text-bp-green font-bold flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-bp-green animate-pulse" />
                PRIMARY CAMERA FEED (CAM-01)
              </span>
              <span className="text-bp-dim text-[11px]">{cam.resolution || '1280x720'} @ {fps.toFixed(1)} FPS</span>
            </div>
            <CameraFeed className="aspect-video" />
          </div>

          {/* Pipeline Architecture Indicator */}
          <div className="p-3 bg-bp-surface border border-bp-border rounded text-[11px] font-mono flex flex-wrap items-center justify-between gap-2 text-bp-dim">
            <span className="text-bp-text font-bold">PIPELINE:</span>
            <span>CAM-01/02</span>
            <span>➔</span>
            <span className="text-bp-green font-bold">YOLO26n</span>
            <span>➔</span>
            <span>BYTE TRACK</span>
            <span>➔</span>
            <span className="text-bp-accent">9-PT ZONE</span>
            <span>➔</span>
            <span>SENSOR FUSION</span>
            <span>➔</span>
            <span className={buzzer ? 'text-bp-danger font-bold animate-pulse' : 'text-bp-dim'}>ESP32 BUZZER</span>
          </div>
        </div>

        {/* Right Telemetry Column */}
        <div className="space-y-3">
          {/* Hardware & Sensor State */}
          <div className="p-3 bg-bp-surface border border-bp-border rounded space-y-2">
            <div className="text-xs font-bold text-bp-green uppercase border-b border-bp-border pb-1 tracking-wider">
              SENSOR TELEMETRY & HARDWARE
            </div>

            {/* Vision Sensor */}
            <div className="flex items-center justify-between py-1 border-b border-bp-border text-xs">
              <span className="text-bp-dim">VISION (YOLO26n)</span>
              <span className="text-bp-green font-bold">REAL TIME</span>
            </div>

            {/* Ground Sensor GPIO26 */}
            <div className="flex items-center justify-between py-1 border-b border-bp-border text-xs">
              <span className="text-bp-dim">GROUND (GPIO26)</span>
              <span className={`font-bold px-2 py-0.5 rounded text-[10px] ${ground.triggered ? 'bg-bp-danger/20 text-bp-danger border border-bp-danger' : 'bg-bp-green/10 text-bp-green border border-bp-green/30'}`}>
                {ground.triggered ? 'TRIGGERED YES (RAW=1)' : 'CLEAR (RAW=0)'}
              </span>
            </div>

            {/* Radar Sensor */}
            <div className="flex items-center justify-between py-1 border-b border-bp-border text-xs">
              <span className="text-bp-dim">RADAR (PROTOTYPE)</span>
              <span className="text-bp-warning text-[10px] border border-bp-warning/40 px-2 py-0.5 rounded">
                SIMULATED ({radar.triggered ? 'ON' : 'OFF'})
              </span>
            </div>

            {/* ESP32 IP */}
            <div className="flex items-center justify-between py-1 text-xs">
              <span className="text-bp-dim">ESP32 HARDWARE</span>
              <span className={esp32.online ? 'text-bp-green font-bold' : 'text-bp-warning'}>
                {esp32.online ? `IP ${esp32.ip || '192.168.137.201'}` : 'DISCONNECTED'}
              </span>
            </div>
          </div>

          {/* Active Alerts Panel */}
          <div className="p-3 bg-bp-surface border border-bp-border rounded space-y-2">
            <div className="text-xs font-bold text-bp-danger uppercase border-b border-bp-border pb-1 tracking-wider flex justify-between items-center">
              <span>ACTIVE ALERTS</span>
              <span className="text-[10px] font-normal text-bp-dim">{activeEvents.length} COUNT</span>
            </div>

            {activeEvents.length === 0 ? (
              <div className="text-center py-6 text-xs text-bp-muted">NO ACTIVE INTRUSIONS</div>
            ) : (
              <div className="space-y-2">
                {activeEvents.map(ev => (
                  <div key={ev.id} className="p-2 bg-bp-danger/10 border border-bp-danger/40 rounded text-xs">
                    <div className="font-bold text-bp-danger">{ev.reason}</div>
                    <div className="text-[10px] text-bp-dim mt-0.5">CODE: {ev.event_code} · CLASS: {ev.class_name}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
