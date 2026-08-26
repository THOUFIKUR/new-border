// BorderPulse — Zone Editor Page
// Smooth polygon drawing using two-layer architecture:
//   Layer 1: Native HTML <img> camera view (non-blinking base64 stream)
//   Layer 2: Interaction canvas (requestAnimationFrame loop, mouse-driven)
//
// Mouse movement NEVER causes React state updates — only useRef.
// requestAnimationFrame drives the cursor preview line.
import { useEffect, useState, useRef, useCallback } from 'react';
import { getZones, createZone, deleteZone, enableZone, disableZone } from '../services/api';
import { useStream } from '../contexts/StreamContext';

// ─── Non-blinking Zone Canvas Layer ───────────────────────────────────────

function ZoneCanvas({ zones, newPoints, onAddPoint, imgSrc, drawing }) {
  const containerRef = useRef(null);
  const interactCanvasRef = useRef(null);
  const mouseRef = useRef({ x: 0, y: 0, inside: false });
  const pointsRef = useRef(newPoints);
  const animFrameRef = useRef(null);
  const drawingRef = useRef(drawing);

  useEffect(() => { pointsRef.current = newPoints; }, [newPoints]);
  useEffect(() => { drawingRef.current = drawing; }, [drawing]);

  const getDisplayDimensions = useCallback(() => {
    const container = containerRef.current;
    if (!container) return { W: 800, H: 450, offsetX: 0, offsetY: 0 };
    const { width: cw, height: ch } = container.getBoundingClientRect();
    const aspectCamera = 16 / 9;
    let W, H, offsetX = 0, offsetY = 0;
    if (cw / ch > aspectCamera) {
      H = ch;
      W = H * aspectCamera;
      offsetX = (cw - W) / 2;
    } else {
      W = cw;
      H = W / aspectCamera;
      offsetY = (ch - H) / 2;
    }
    return { W, H, offsetX, offsetY };
  }, []);

  const resizeCanvas = useCallback(() => {
    const container = containerRef.current;
    const ic = interactCanvasRef.current;
    if (!container || !ic) return;
    const { width, height } = container.getBoundingClientRect();
    if (ic.width !== Math.round(width) || ic.height !== Math.round(height)) {
      ic.width = Math.round(width);
      ic.height = Math.round(height);
    }
  }, []);

  const drawInteraction = useCallback(() => {
    const canvas = interactCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const { W, H, offsetX, offsetY } = getDisplayDimensions();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const toPixel = (nx, ny) => ({
      px: offsetX + nx * W,
      py: offsetY + ny * H,
    });

    // Draw existing saved zones
    zones.forEach(zone => {
      if (!zone.polygon_points || zone.polygon_points.length < 3) return;
      ctx.beginPath();
      const { px: x0, py: y0 } = toPixel(zone.polygon_points[0].x, zone.polygon_points[0].y);
      ctx.moveTo(x0, y0);
      zone.polygon_points.slice(1).forEach(p => {
        const { px, py } = toPixel(p.x, p.y);
        ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.fillStyle = zone.enabled ? 'rgba(0, 255, 102, 0.12)' : 'rgba(82, 102, 115, 0.08)';
      ctx.strokeStyle = zone.enabled ? '#00FF66' : '#526673';
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();

      const cx = zone.polygon_points.reduce((a, p) => a + p.x, 0) / zone.polygon_points.length;
      const cy = zone.polygon_points.reduce((a, p) => a + p.y, 0) / zone.polygon_points.length;
      const { px: lx, py: ly } = toPixel(cx, cy);
      ctx.fillStyle = zone.enabled ? '#00FF66' : '#8A9EA8';
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(zone.name, lx, ly);
    });

    if (!drawingRef.current) {
      animFrameRef.current = requestAnimationFrame(drawInteraction);
      return;
    }

    const pts = pointsRef.current;
    const mouse = mouseRef.current;

    if (pts.length > 0) {
      ctx.beginPath();
      const { px: sx, py: sy } = toPixel(pts[0].x, pts[0].y);
      ctx.moveTo(sx, sy);
      pts.slice(1).forEach(p => {
        const { px, py } = toPixel(p.x, p.y);
        ctx.lineTo(px, py);
      });
      ctx.strokeStyle = '#FFB700';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      pts.forEach(p => {
        const { px, py } = toPixel(p.x, p.y);
        ctx.beginPath();
        ctx.arc(px, py, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#FFB700';
        ctx.fill();
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      if (mouse.inside) {
        const last = pts[pts.length - 1];
        const { px: lx, py: ly } = toPixel(last.x, last.y);
        ctx.beginPath();
        ctx.moveTo(lx, ly);
        ctx.lineTo(mouse.x, mouse.y);
        ctx.strokeStyle = 'rgba(255, 183, 0, 0.6)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    if (mouse.inside) {
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.8)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(mouse.x - 10, mouse.y);
      ctx.lineTo(mouse.x + 10, mouse.y);
      ctx.moveTo(mouse.x, mouse.y - 10);
      ctx.lineTo(mouse.x, mouse.y + 10);
      ctx.stroke();
    }

    animFrameRef.current = requestAnimationFrame(drawInteraction);
  }, [zones, getDisplayDimensions]);

  useEffect(() => {
    animFrameRef.current = requestAnimationFrame(drawInteraction);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [drawInteraction]);

  useEffect(() => {
    resizeCanvas();
    const container = containerRef.current;
    if (!container) return;
    const ro = new ResizeObserver(() => resizeCanvas());
    ro.observe(container);
    return () => ro.disconnect();
  }, [resizeCanvas]);

  const handleMouseMove = useCallback((e) => {
    const canvas = interactCanvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    mouseRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      inside: true,
    };
  }, []);

  const handleMouseLeave = useCallback(() => {
    mouseRef.current = { ...mouseRef.current, inside: false };
  }, []);

  const handleClick = useCallback((e) => {
    if (!onAddPoint || !drawingRef.current) return;
    const canvas = interactCanvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const { W, H, offsetX, offsetY } = getDisplayDimensions();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;
    const nx = Math.max(0, Math.min(1, (canvasX - offsetX) / W));
    const ny = Math.max(0, Math.min(1, (canvasY - offsetY) / H));
    onAddPoint({ x: nx, y: ny });
  }, [onAddPoint, getDisplayDimensions]);

  return (
    <div
      ref={containerRef}
      className="relative w-full rounded-lg border border-bp-border overflow-hidden bg-bp-bg"
      style={{ height: '48vh', minHeight: '300px' }}
    >
      {/* Layer 1: Native Non-Blinking Camera Feed */}
      {imgSrc ? (
        <img
          src={imgSrc}
          alt="Live Feed"
          className="absolute inset-0 w-full h-full object-contain pointer-events-none"
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center text-bp-muted font-mono text-xs bg-bp-surface">
          CAMERA FEED OFFLINE
        </div>
      )}
      {/* Layer 2: Interaction Overlay */}
      <canvas
        ref={interactCanvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ cursor: drawing ? 'crosshair' : 'default' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
      />
    </div>
  );
}

// ─── Zones Page ───────────────────────────────────────────────────────────

export default function Zones() {
  const { streamData } = useStream();
  const [zones,     setZones]     = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [drawing,   setDrawing]   = useState(false);
  const [newPoints, setNewPoints] = useState([]);
  const [newName,   setNewName]   = useState('Restricted Zone 01');

  const imgSrc = streamData?.frame ? `data:image/jpeg;base64,${streamData.frame}` : null;

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    try {
      const data = await getZones();
      const unique = [];
      const seen = new Set();
      (data.zones || []).forEach(z => {
        if (!seen.has(z.id)) {
          seen.add(z.id);
          unique.push(z);
        }
      });
      setZones(unique);
    } catch (e) {
      console.error('Get zones error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(true); }, [load]);

  const addPoint = useCallback((pt) => {
    if (!drawing) return;
    setNewPoints(prev => [...prev, pt]);
  }, [drawing]);

  const saveZone = async () => {
    if (newPoints.length < 3) { alert('Need at least 3 points'); return; }
    try {
      const created = await createZone({
        name: newName,
        polygon_points: newPoints,
        zone_type: 'restricted',
        enabled: true,
        alert_on_classes: ['person'],
      });
      setNewPoints([]);
      setDrawing(false);
      if (created && created.zone) {
        setZones(prev => [...prev.filter(z => z.id !== created.zone.id), created.zone]);
      }
      await load(false);
    } catch (e) {
      console.error('Save zone error:', e);
    }
  };

  const cancelDraw = useCallback(() => {
    setDrawing(false);
    setNewPoints([]);
  }, []);

  const toggleZone = async (zone) => {
    setZones(prev => prev.map(z => z.id === zone.id ? { ...z, enabled: !z.enabled } : z));
    try {
      if (zone.enabled) await disableZone(zone.id);
      else await enableZone(zone.id);
    } catch (e) {
      console.error('Toggle zone error:', e);
      await load(false);
    }
  };

  const removeZone = async (id) => {
    if (!confirm('Delete this zone?')) return;
    setZones(prev => prev.filter(z => z.id !== id));
    try {
      await deleteZone(id);
    } catch (e) {
      console.error('Delete zone error:', e);
      await load(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-bp-text bg-bp-bg">
      <div className="flex justify-between items-center pb-2 border-b border-bp-border">
        <div>
          <h1 className="text-lg font-bold text-bp-green tracking-wider uppercase font-sans">04 RESTRICTED ZONES</h1>
          <p className="text-xs text-bp-muted">DRAW POLYGON BOUNDARIES. PERSON INTRUSION EVALUATES 9 BODY REPRESENTATIVE POINTS.</p>
        </div>
        {drawing ? (
          <div className="flex gap-2 items-center">
            <input
              value={newName}
              onChange={e => setNewName(e.target.value)}
              className="bg-bp-surface border border-bp-border rounded px-2 py-1 text-xs text-bp-text w-44 font-mono"
              placeholder="Zone Name"
            />
            <button
              onClick={saveZone}
              disabled={newPoints.length < 3}
              className="px-3 py-1 rounded text-xs font-bold bg-bp-green/20 border border-bp-green text-bp-green hover:bg-bp-green/30 disabled:opacity-50"
            >
              SAVE ({newPoints.length} PTS)
            </button>
            <button
              onClick={cancelDraw}
              className="px-3 py-1 rounded text-xs font-bold bg-bp-surface border border-bp-border text-bp-dim hover:text-bp-text"
            >
              CANCEL
            </button>
          </div>
        ) : (
          <button
            onClick={() => setDrawing(true)}
            className="px-4 py-1.5 rounded text-xs font-bold bg-bp-green border border-bp-green text-black hover:bg-bp-green/90 shadow-[0_0_10px_rgba(0,255,102,0.2)]"
          >
            + DRAW RESTRICTED ZONE
          </button>
        )}
      </div>

      {/* Non-Blinking Zone Canvas Layer */}
      <ZoneCanvas
        zones={zones}
        newPoints={newPoints}
        onAddPoint={addPoint}
        imgSrc={imgSrc}
        drawing={drawing}
      />

      {drawing && (
        <div className="text-xs text-bp-warning text-center font-mono">
          Click on camera feed to add polygon vertices.
          {newPoints.length < 3 && ` Need ${3 - newPoints.length} more.`}
          {newPoints.length >= 3 && ' ✓ Click SAVE ZONE when finished.'}
        </div>
      )}

      {/* Zone Cards List */}
      {loading ? (
        <div className="text-center py-6 text-xs text-bp-muted font-mono animate-pulse">Loading active zones...</div>
      ) : (
        <div className="space-y-2">
          {zones.length === 0 && (
            <div className="text-center py-8 text-xs text-bp-muted border border-bp-border rounded bg-bp-surface font-mono">
              NO RESTRICTED ZONES CONFIGURED — CLICK '+ DRAW RESTRICTED ZONE' ABOVE
            </div>
          )}
          {zones.map(z => (
            <div key={z.id} className="p-3 bg-bp-surface border border-bp-border rounded flex items-center justify-between font-mono">
              <div className="flex items-center gap-3">
                <span className={`w-2.5 h-2.5 rounded-full ${z.enabled ? 'bg-bp-green shadow-[0_0_6px_#00FF66]' : 'bg-bp-muted'}`} />
                <div>
                  <div className="text-xs font-bold text-bp-text tracking-wider">{z.name}</div>
                  <div className="text-[11px] text-bp-dim">
                    {z.polygon_points?.length || 0} POINTS · TYPE: {z.zone_type?.toUpperCase() || 'RESTRICTED'} · CLASS: {(z.alert_on_classes || ['person']).join(', ')}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleZone(z)}
                  className={`px-3 py-1 rounded text-[11px] font-bold border transition-all ${
                    z.enabled
                      ? 'bg-bp-warning/10 border-bp-warning text-bp-warning hover:bg-bp-warning/20'
                      : 'bg-bp-green/10 border-bp-green text-bp-green hover:bg-bp-green/20'
                  }`}
                >
                  {z.enabled ? 'DISABLE' : 'ENABLE'}
                </button>
                <button
                  onClick={() => removeZone(z.id)}
                  className="px-3 py-1 rounded text-[11px] font-bold bg-bp-danger/10 border border-bp-danger text-bp-danger hover:bg-bp-danger/20"
                >
                  DELETE
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
