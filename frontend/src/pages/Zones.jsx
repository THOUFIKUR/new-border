// BorderPulse — Zone Editor Page
// Interactive polygon zone drawing on camera canvas
import { useEffect, useState, useRef, useCallback } from 'react';
import { getZones, createZone, deleteZone, enableZone, disableZone } from '../services/api';
import { Card, SectionHeader, Btn, Spinner } from '../components/ui';
import { useStream } from '../contexts/StreamContext';

function ZoneCanvas({ zones, newPoints, onAddPoint, imgSrc }) {
  const canvasRef = useRef(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Draw background image if available
    if (imgSrc) {
      const img = new Image();
      img.onload = () => ctx.drawImage(img, 0, 0, W, H);
      img.src = imgSrc;
    } else {
      ctx.fillStyle = '#080d1a';
      ctx.fillRect(0, 0, W, H);
    }

    // Draw existing zones
    zones.forEach(zone => {
      if (zone.polygon_points.length < 3) return;
      ctx.beginPath();
      ctx.moveTo(zone.polygon_points[0].x * W, zone.polygon_points[0].y * H);
      zone.polygon_points.slice(1).forEach(p => ctx.lineTo(p.x * W, p.y * H));
      ctx.closePath();
      ctx.fillStyle = zone.enabled ? 'rgba(0,212,255,0.12)' : 'rgba(100,100,100,0.1)';
      ctx.strokeStyle = zone.enabled ? '#00d4ff' : '#6b7fa3';
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();
      // Label
      const cx = zone.polygon_points.reduce((a, p) => a + p.x, 0) / zone.polygon_points.length;
      const cy = zone.polygon_points.reduce((a, p) => a + p.y, 0) / zone.polygon_points.length;
      ctx.fillStyle = zone.enabled ? '#00d4ff' : '#6b7fa3';
      ctx.font = '12px Inter';
      ctx.textAlign = 'center';
      ctx.fillText(zone.name, cx * W, cy * H);
    });

    // Draw new polygon being drawn
    if (newPoints.length > 0) {
      ctx.beginPath();
      ctx.moveTo(newPoints[0].x * W, newPoints[0].y * H);
      newPoints.slice(1).forEach(p => ctx.lineTo(p.x * W, p.y * H));
      ctx.strokeStyle = '#ffaa00';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
      newPoints.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x * W, p.y * H, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#ffaa00';
        ctx.fill();
      });
    }
  }, [zones, newPoints, imgSrc]);

  useEffect(() => { draw(); }, [draw]);

  const handleClick = (e) => {
    if (!onAddPoint) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    onAddPoint({ x, y });
  };

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={450}
      className="w-full rounded-lg border border-bp-border cursor-crosshair"
      onClick={handleClick}
      style={{ maxHeight: '45vh', objectFit: 'contain' }}
    />
  );
}

export default function Zones() {
  const { streamData } = useStream();
  const [zones,     setZones]     = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [drawing,   setDrawing]   = useState(false);
  const [newPoints, setNewPoints] = useState([]);
  const [newName,   setNewName]   = useState('Restricted Zone');

  const imgSrc = streamData?.frame ? `data:image/jpeg;base64,${streamData.frame}` : null;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getZones();
      setZones(data.zones || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const addPoint = (pt) => {
    if (!drawing) return;
    setNewPoints(prev => [...prev, pt]);
  };

  const saveZone = async () => {
    if (newPoints.length < 3) { alert('Need at least 3 points'); return; }
    try {
      await createZone({
        name: newName,
        polygon_points: newPoints,
        zone_type: 'restricted',
        enabled: true,
        alert_on_classes: ['person'],
      });
      setNewPoints([]);
      setDrawing(false);
      await load();
    } catch (e) { console.error(e); }
  };

  const toggleZone = async (zone) => {
    try {
      if (zone.enabled) await disableZone(zone.id);
      else await enableZone(zone.id);
      await load();
    } catch (e) { console.error(e); }
  };

  const removeZone = async (id) => {
    if (!confirm('Delete this zone?')) return;
    try { await deleteZone(id); await load(); } catch (e) { console.error(e); }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <SectionHeader
        title="Restricted Zones"
        subtitle="Draw polygon zones on the camera view. Person bottom-center must enter zone to trigger."
        actions={
          drawing ? (
            <div className="flex gap-2 items-center">
              <input
                value={newName}
                onChange={e => setNewName(e.target.value)}
                className="bg-bp-card border border-bp-border rounded px-2 py-1 text-sm text-bp-text w-36"
              />
              <Btn variant="success" onClick={saveZone} disabled={newPoints.length < 3}>
                Save ({newPoints.length} pts)
              </Btn>
              <Btn variant="ghost" onClick={() => { setDrawing(false); setNewPoints([]); }}>Cancel</Btn>
            </div>
          ) : (
            <Btn variant="primary" onClick={() => setDrawing(true)}>+ Draw Zone</Btn>
          )
        }
      />

      {/* Canvas */}
      <ZoneCanvas zones={zones} newPoints={newPoints} onAddPoint={addPoint} imgSrc={imgSrc} />
      {drawing && (
        <div className="text-xs text-yellow-500 text-center">
          Click on the canvas to add polygon points. {newPoints.length < 3 && `Need ${3 - newPoints.length} more.`}
        </div>
      )}

      {/* Zone list */}
      {loading ? <Spinner /> : (
        <div className="space-y-2">
          {zones.length === 0 && (
            <Card className="text-center py-8 text-bp-muted">No zones defined — draw one above</Card>
          )}
          {zones.map(z => (
            <Card key={z.id} className="flex items-center gap-3">
              <span className={`status-dot ${z.enabled ? 'dot-online' : 'dot-offline'}`} />
              <div className="flex-1">
                <div className="text-sm font-semibold text-bp-text">{z.name}</div>
                <div className="text-xs text-bp-muted">
                  {z.polygon_points.length} points · Type: {z.zone_type}
                  · Classes: {(z.alert_on_classes || ['person']).join(', ')}
                </div>
              </div>
              <div className="flex gap-2">
                <Btn variant={z.enabled ? 'warning' : 'success'} size="sm" onClick={() => toggleZone(z)}>
                  {z.enabled ? 'Disable' : 'Enable'}
                </Btn>
                <Btn variant="danger" size="sm" onClick={() => removeZone(z.id)}>Delete</Btn>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Card className="text-xs text-bp-muted">
        <div className="font-semibold text-bp-dim mb-1">How zones work</div>
        <ul className="space-y-1 list-disc pl-4">
          <li>Coordinates are normalized 0.0–1.0 and stored in Supabase</li>
          <li>The bottom-center of each bounding box is the detection point</li>
          <li>Point-in-polygon uses ray-casting (no external dependency)</li>
          <li>Only enabled zones trigger alerts</li>
          <li>Class filter controls which object classes trigger each zone</li>
        </ul>
      </Card>
    </div>
  );
}
