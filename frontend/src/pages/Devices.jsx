// BorderPulse — Devices Page
import { useEffect, useState } from 'react';
import { useStream } from '../contexts/StreamContext';
import { getDevices, getCameras, testBuzzer } from '../services/api';
import { Card, SectionHeader, StatusDot, Btn, Spinner } from '../components/ui';

export default function Devices() {
  const { streamData } = useStream();
  const [cameras,  setCameras]  = useState([]);
  const [devices,  setDevices]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [buzzerOk, setBuzzerOk] = useState(null);

  const esp32 = streamData?.esp32_status ?? {};

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [c, d] = await Promise.all([getCameras(), getDevices()]);
        setCameras(c.cameras || []);
        setDevices(d.devices || []);
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    load();
  }, []);

  const testBuzz = async () => {
    try {
      const r = await testBuzzer();
      setBuzzerOk(r.success);
      setTimeout(() => setBuzzerOk(null), 3000);
    } catch { setBuzzerOk(false); }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <SectionHeader title="Devices" subtitle="Camera and ESP32 hardware status" />

      {loading ? <Spinner /> : (
        <>
          {/* Cameras */}
          <div>
            <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Cameras</div>
            <div className="space-y-2">
              {cameras.map((c, i) => {
                const live = streamData?.camera_status;
                const online = live?.online ?? c.status === 'online';
                return (
                  <Card key={i}>
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl border ${online ? 'border-green-700 bg-green-900/20' : 'border-red-700 bg-red-900/20'}`}>
                        ◎
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <StatusDot status={online ? 'online' : 'offline'} />
                          <span className="text-sm font-semibold">{c.name || 'Camera'}</span>
                        </div>
                        <div className="text-xs text-bp-muted mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
                          <span>Type: <span className="text-bp-dim">{c.source_type}</span></span>
                          <span>Code: <span className="mono text-bp-dim">{c.camera_code}</span></span>
                          <span>Resolution: <span className="mono text-bp-dim">{live?.resolution || c.resolution || '—'}</span></span>
                          <span>FPS: <span className="mono text-bp-dim">{live?.fps?.toFixed(1) || '—'}</span></span>
                        </div>
                        {(live?.error || c.error) && (
                          <div className="text-xs text-red-400 mt-1">{live?.error || c.error}</div>
                        )}
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* ESP32 */}
          <div>
            <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">ESP32 Controller</div>
            <Card className={esp32.online ? 'border-green-700/40' : 'border-red-700/40'}>
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl border ${esp32.online ? 'border-green-700 bg-green-900/20' : 'border-red-700 bg-red-900/20'}`}>
                  ⬡
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <StatusDot status={esp32.online ? 'online' : 'offline'} />
                    <span className="text-sm font-semibold">{esp32.online ? 'ESP32 ONLINE' : 'ESP32 OFFLINE'}</span>
                  </div>
                  <div className="text-xs text-bp-muted mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
                    <span>IP: <span className="mono text-bp-dim">{esp32.ip || '—'}</span></span>
                    <span>Firmware: <span className="mono text-bp-dim">{esp32.firmware_version || '—'}</span></span>
                    <span>Buzzer: <span className={esp32.buzzer_active ? 'text-red-400' : 'text-bp-dim'}>
                      {esp32.buzzer_active ? 'ACTIVE' : 'Idle'}
                    </span></span>
                    <span>Last seen: <span className="mono text-bp-dim">
                      {esp32.last_seen ? new Date(esp32.last_seen * 1000).toLocaleTimeString() : '—'}
                    </span></span>
                  </div>
                  {esp32.error && <div className="text-xs text-red-400 mt-1">{esp32.error}</div>}
                </div>
                <div className="flex gap-2">
                  <Btn
                    variant="primary"
                    size="sm"
                    onClick={testBuzz}
                    disabled={!esp32.online}
                  >
                    Test Buzzer
                  </Btn>
                </div>
              </div>
              {buzzerOk !== null && (
                <div className={`mt-3 text-xs px-3 py-2 rounded ${buzzerOk ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>
                  {buzzerOk ? '✓ Buzzer test sent successfully' : '✗ Buzzer test failed — ESP32 may be offline'}
                </div>
              )}
              {!esp32.online && (
                <div className="mt-3 text-xs text-yellow-600/80 bg-yellow-900/10 rounded p-2 border border-yellow-700/30">
                  ESP32 is offline. Vision pipeline continues normally.
                  Configure Wi-Fi in <span className="mono">esp32/firmware/borderpulse_esp32.ino</span> and flash to device.
                </div>
              )}
            </Card>
          </div>

          {/* ESP32 setup guide */}
          <Card>
            <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">ESP32 Hardware Notes</div>
            <div className="space-y-2 text-xs text-bp-dim">
              <div className="flex gap-2"><span className="text-yellow-500">⚠</span><span>Verify exact ESP32 chip variant before wiring sensors</span></div>
              <div className="flex gap-2"><span className="text-yellow-500">⚠</span><span>GPIO25 (Buzzer), GPIO26 (Ground sensor), GPIO27 (Radar OUT) are PROVISIONAL</span></div>
              <div className="flex gap-2"><span className="text-yellow-500">⚠</span><span>Confirm voltage compatibility (3.3V GPIO) before connecting sensors</span></div>
              <div className="flex gap-2"><span className="text-blue-400">ℹ</span><span>Configure WIFI_SSID and WIFI_PASSWORD in the .ino file before flashing</span></div>
              <div className="flex gap-2"><span className="text-blue-400">ℹ</span><span>Update ESP32_IP in <span className="mono">.env</span> to match the ESP32 assigned IP</span></div>
              <div className="flex gap-2"><span className="text-green-400">✓</span><span>When offline, all vision/zone/event processing continues without interruption</span></div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
