// BorderPulse — Zone Editor Page
// Smooth polygon drawing using two-layer canvas architecture:
//   Layer 1: Camera image (static, updated by WebSocket frame)
//   Layer 2: Interaction canvas (requestAnimationFrame loop, mouse-driven)
//
// Mouse movement NEVER causes React state updates — only useRef.
// requestAnimationFrame drives the cursor preview line.
// React state only updates on: addPoint, save, cancel, zone list changes.
import { useEffect, useState, useRef, useCallback } from 'react';
import { getZones, createZone, deleteZone, enableZone, disableZone } from '../services/api';
import { Card, SectionHeader, Btn, Spinner } from '../components/ui';
import { useStream } from '../contexts/StreamContext';

// ─── Two-layer Zone Canvas ────────────────────────────────────────────────

function ZoneCanvas({ zones, newPoints, onAddPoint, imgSrc, drawing }) {
  const containerRef = useRef(null);
  const cameraCanvasRef = useRef(null);  // Camera layer — draw latest JPEG
  const interactCanvasRef = useRef(null); // Interaction layer — RAF loop
  const mouseRef = useRef({ x: 0, y: 0, inside: false });
  const pointsRef = useRef(newPoints);     // Mirror of newPoints without re-render
  const animFrameRef = useRef(null);
  const drawingRef = useRef(drawing);

  // Keep refs in sync with props
  useEffect(() => { pointsRef.current = newPoints; }, [newPoints]);
  useEffect(() => { drawingRef.current = drawing; }, [drawing]);

  // ── Compute display dimensions accounting for object-fit ──────────────
  const getDisplayDimensions = useCallback(() => {
    const container = containerRef.current;
    if (!container) return { W: 800, H: 450, offsetX: 0, offsetY: 0 };
    const { width: cw, height: ch } = container.getBoundingClientRect();
    const aspectCamera = 16 / 9;  // Expected camera aspect ratio
    let W, H, offsetX = 0, offsetY = 0;
    if (cw / ch > aspectCamera) {
      // Pillarboxed: height fits, width letterboxed
      H = ch;
      W = H * aspectCamera;
      offsetX = (cw - W) / 2;
    } else {
      // Letterboxed: width fits, height pillarboxed
      W = cw;
      H = W / aspectCamera;
      offsetY = (ch - H) / 2;
    }
    return { W, H, offsetX, offsetY };
  }, []);

  // ── Resize canvases ───────────────────────────────────────────────────
  const resizeCanvases = useCallback(() => {
    const container = containerRef.current;
    const cc = cameraCanvasRef.current;
    const ic = interactCanvasRef.current;
    if (!container || !cc || !ic) return;
    const { width, height } = container.getBoundingClientRect();
    if (cc.width !== Math.round(width) || cc.height !== Math.round(height)) {
      cc.width = Math.round(width);
      cc.height = Math.round(height);
      ic.width = Math.round(width);
      ic.height = Math.round(height);
    }
  }, []);

  // ── Draw camera layer ─────────────────────────────────────────────────
  const drawCamera = useCallback(() => {
    const canvas = cameraCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const CW = canvas.width, CH = canvas.height;
    const { W, H, offsetX, offsetY } = getDisplayDimensions();
    ctx.clearRect(0, 0, CW, CH);

    if (imgSrc) {
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, offsetX, offsetY, W, H);
      };
      img.src = imgSrc;
    } else {
      ctx.fillStyle = '#080d1a';
      ctx.fillRect(offsetX, offsetY, W, H);
      ctx.fillStyle = '#1a2d47';
      ctx.font = '14px Inter, monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Camera Offline', offsetX + W / 2, offsetY + H / 2);
    }
  }, [imgSrc, getDisplayDimensions]);

  // ── RAF loop: draw interaction layer ─────────────────────────────────
  const drawInteraction = useCallback(() => {
    const canvas = interactCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const { W, H, offsetX, offsetY } = getDisplayDimensions();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Helper: normalised → canvas pixel
    const toPixel = (nx, ny) => ({
      px: offsetX + nx * W,
      py: offsetY + ny * H,
    });

    // Draw existing saved zones
    zones.forEach(zone => {
      if (zone.polygon_points.length < 3) return;
      ctx.beginPath();
      const { px: x0, py: y0 } = toPixel(zone.polygon_points[0].x, zone.polygon_points[0].y);
      ctx.moveTo(x0, y0);
      zone.polygon_points.slice(1).forEach(p => {
        const { px, py } = toPixel(p.x, p.y);
        ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.fillStyle = zone.enabled ? 'rgba(0,212,255,0.12)' : 'rgba(100,100,100,0.08)';
      ctx.strokeStyle = zone.enabled ? '#00d4ff' : '#6b7fa3';
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();
      // Zone label
      const cx = zone.polygon_points.reduce((a, p) => a + p.x, 0) / zone.polygon_points.length;
      const cy = zone.polygon_points.reduce((a, p) => a + p.y, 0) / zone.polygon_points.length;
      const { px: lx, py: ly } = toPixel(cx, cy);
      ctx.fillStyle = zone.enabled ? '#00d4ff' : '#6b7fa3';
      ctx.font = '12px Inter, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(zone.name, lx, ly);
    });

    if (!drawingRef.current) {
      animFrameRef.current = requestAnimationFrame(drawInteraction);
      return;
    }

    const pts = pointsRef.current;
    const mouse = mouseRef.current;

    // Draw polygon being drawn (dashed outline)
    if (pts.length > 0) {
      ctx.beginPath();
      const { px: sx, py: sy } = toPixel(pts[0].x, pts[0].y);
      ctx.moveTo(sx, sy);
      pts.slice(1).forEach(p => {
        const { px, py } = toPixel(p.x, p.y);
        ctx.lineTo(px, py);
      });
      ctx.strokeStyle = '#ffaa00';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw point dots
      pts.forEach(p => {
        const { px, py } = toPixel(p.x, p.y);
        ctx.beginPath();
        ctx.arc(px, py, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#ffaa00';
        ctx.fill();
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      // Live cursor-to-last-point preview line
      if (mouse.inside) {
        const last = pts[pts.length - 1];
        const { px: lx, py: ly } = toPixel(last.x, last.y);
        ctx.beginPath();
        ctx.moveTo(lx, ly);
        ctx.lineTo(mouse.x, mouse.y);
        ctx.strokeStyle = 'rgba(255,170,0,0.5)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Closing line hint (last point → first point, very faint)
        if (pts.length >= 2) {
          const { px: fx, py: fy } = toPixel(pts[0].x, pts[0].y);
          ctx.beginPath();
          ctx.moveTo(mouse.x, mouse.y);
          ctx.lineTo(fx, fy);
          ctx.strokeStyle = 'rgba(255,170,0,0.18)';
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 6]);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }
    }

    // Crosshair cursor
    if (mouse.inside) {
      ctx.strokeStyle = 'rgba(255,255,255,0.6)';
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

  // ── Start RAF loop ────────────────────────────────────────────────────
  useEffect(() => {
    animFrameRef.current = requestAnimationFrame(drawInteraction);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [drawInteraction]);

  // ── Camera layer: update when frame changes ───────────────────────────
  useEffect(() => {
    resizeCanvases();
    drawCamera();
  }, [imgSrc, drawCamera, resizeCanvases]);

  // ── ResizeObserver ────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      resizeCanvases();
      drawCamera();
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [resizeCanvases, drawCamera]);

  // ── Mouse handlers (use refs, no setState) ────────────────────────────
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
    // Normalise to 0–1 within the camera display area
    const nx = Math.max(0, Math.min(1, (canvasX - offsetX) / W));
    const ny = Math.max(0, Math.min(1, (canvasY - offsetY) / H));
    onAddPoint({ x: nx, y: ny });
  }, [onAddPoint, getDisplayDimensions]);

  return (
    <div
      ref={containerRef}
      className="relative w-full rounded-lg border border-bp-border overflow-hidden bg-bp-bg"
      style={{ height: '45vh', minHeight: '280px' }}
    >
      {/* Layer 1: Camera */}
      <canvas
        ref={cameraCanvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ pointerEvents: 'none' }}
      />
      {/* Layer 2: Interaction (receives all pointer events) */}
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

  // addPoint only updates state on click — no setState on mousemove
  const addPoint = useCallback((pt) => {
    if (!drawing) return;
    setNewPoints(prev => [...prev, pt]);
  }, [drawing]);

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

  const cancelDraw = useCallback(() => {
    setDrawing(false);
    setNewPoints([]);
  }, []);

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
              <Btn variant="ghost" onClick={cancelDraw}>Cancel</Btn>
            </div>
          ) : (
            <Btn variant="primary" onClick={() => setDrawing(true)}>+ Draw Zone</Btn>
          )
        }
      />

      {/* Canvas — two-layer smooth editor */}
      <ZoneCanvas
        zones={zones}
        newPoints={newPoints}
        onAddPoint={addPoint}
        imgSrc={imgSrc}
        drawing={drawing}
      />

      {drawing && (
        <div className="text-xs text-yellow-500 text-center">
          Click on the camera to add polygon points.
          {newPoints.length < 3 && ` Need ${3 - newPoints.length} more.`}
          {newPoints.length >= 3 && ' ✓ Click Save or add more points.'}
        </div>
      )}

      {/* Zone list */}
      {loading ? <Spinner /> : (
        <div className="space-y-2">
          {zones.length === 0 && (
            <Card className="text-center py-8 text-bp-muted">No zones defined — click '+ Draw Zone' above</Card>
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
          <li>Coordinates are normalised 0.0–1.0 and stored in Supabase</li>
          <li>The bottom-center of each bounding box is the detection point</li>
          <li>Point-in-polygon uses ray-casting (no external dependency)</li>
          <li>Only enabled zones trigger alerts</li>
          <li>Person must appear in zone for {'{PERSON_CONFIRMATION_FRAMES}'} frames before alarm fires</li>
        </ul>
      </Card>
    </div>
  );
}
