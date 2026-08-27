// BorderPulse — Camera Health Page
import { useEffect, useState } from 'react';
import { getCameraHealth } from '../services/api';
import { Card, SectionHeader, StatCard, Spinner } from '../components/ui';
import { useStream } from '../contexts/StreamContext';

const STATE_COLORS = {
  HEALTHY:        'text-bp-safe',
  WARNING:        'text-yellow-400',
  DARK:           'text-blue-400',
  BLURRED:        'text-orange-400',
  BLOCKED:        'text-red-400',
  LOW_VISIBILITY: 'text-yellow-500',
  OFFLINE:        'text-bp-danger',
};
const STATE_ICONS = {
  HEALTHY: '✓', WARNING: '⚠', DARK: '🌑', BLURRED: '~',
  BLOCKED: '⊘', LOW_VISIBILITY: '≈', OFFLINE: '✕',
};

export default function CameraHealth() {
  const { streamData } = useStream();
  const [health,   setHealth]   = useState(null);
  const [loading,  setLoading]  = useState(true);

  const load = async () => {
    try {
      const data = await getCameraHealth();
      setHealth(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const h   = health?.camera_health ?? {};
  const cam = streamData?.camera_status ?? {};
  const state = h.state || 'OFFLINE';

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <SectionHeader title="Camera Health" subtitle="Image quality metrics and camera diagnostics" />

      {loading ? <Spinner /> : (
        <>
          {/* State badge */}
          <Card className={`border ${state === 'HEALTHY' ? 'border-green-700/40' : state === 'OFFLINE' ? 'border-red-700/40' : 'border-yellow-700/40'}`}>
            <div className="flex items-center gap-4">
              <div className={`text-5xl font-bold ${STATE_COLORS[state] || 'text-bp-muted'}`}>
                {STATE_ICONS[state] || '?'}
              </div>
              <div>
                <div className={`text-2xl font-bold ${STATE_COLORS[state] || 'text-bp-muted'}`}>{state}</div>
                <div className="text-sm text-bp-muted mt-0.5">{h.message || 'No data'}</div>
              </div>
            </div>
          </Card>

          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Camera FPS"   value={(cam.fps || h.fps || 0).toFixed(1)} unit="fps" color={cam.fps > 10 ? 'text-bp-safe' : 'text-bp-danger'} />
            <StatCard label="Brightness"   value={(h.brightness_score || 0).toFixed(0)} unit="/255" color="text-bp-accent" />
            <StatCard label="Sharpness"    value={(h.blur_score || 0).toFixed(0)} unit="var" color="text-bp-accent" />
            <StatCard label="Contrast"     value={((h.visibility_score || 0) * 100).toFixed(1)} unit="%" color="text-bp-accent" />
          </div>

          {/* Detail table */}
          <Card>
            <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Metric Thresholds</div>
            <div className="space-y-2 text-xs">
              {[
                { label: 'Brightness',       value: h.brightness_score?.toFixed(1), note: '< 25 = DARK, < 5 = BLOCKED',  good: h.brightness_score > 25 },
                { label: 'Sharpness (Lap.)', value: h.blur_score?.toFixed(1),       note: '< 100 = BLURRED',              good: h.blur_score > 100 },
                { label: 'RMS Contrast',     value: ((h.visibility_score||0)*100).toFixed(1)+'%', note: '< 5% = LOW_VISIBILITY', good: h.visibility_score > 0.05 },
                { label: 'Camera FPS',       value: cam.fps?.toFixed(1),            note: 'Target: 15+ fps',              good: cam.fps > 10 },
                { label: 'Resolution',       value: cam.resolution,                 note: 'Preferred: 1280x720',          good: !!cam.resolution },
                { label: 'Frame Count',      value: health?.frame_count,            note: 'Total frames captured' },
              ].map(({ label, value, note, good }) => (
                <div key={label} className="flex items-center justify-between py-1.5 border-b border-bp-border last:border-0">
                  <div>
                    <span className="text-bp-text">{label}</span>
                    <span className="text-bp-muted ml-2">({note})</span>
                  </div>
                  <span className={`mono font-semibold ${good === true ? 'text-bp-safe' : good === false ? 'text-bp-danger' : 'text-bp-dim'}`}>
                    {value ?? '—'}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Methodology note */}
          <Card className="text-xs text-bp-muted">
            <div className="font-semibold text-bp-dim mb-1">Detection Methodology</div>
            <ul className="space-y-1 list-disc pl-4">
              <li>Brightness: mean pixel value of grayscale frame</li>
              <li>Sharpness: Laplacian variance (higher = sharper)</li>
              <li>Contrast: normalized RMS standard deviation</li>
              <li>Low visibility may indicate fog/haze — EXPERIMENTAL classification only</li>
              <li>Physical camera obstruction cannot be confirmed from software alone</li>
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
