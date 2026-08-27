// BorderPulse — Live Camera Feed with detection overlays
import { useStream } from '../contexts/StreamContext';

export default function CameraFeed({ className = '', showOverlay = true, camId = 'cam_01' }) {
  const { streamData, connected } = useStream();

  const camData  = streamData?.cameras?.[camId];
  const frame    = camData?.frame || streamData?.frame;
  const cam      = camData || streamData?.camera_status;
  const fps      = cam?.fps ?? streamData?.camera_status?.fps ?? 0;
  const latency  = streamData?.inference_latency_ms ?? 0;
  const decision = streamData?.decision_state ?? '';

  const dangerLabel = decision.includes('CRITICAL') || decision.includes('CONFIRMED');
  const warningLabel = decision.includes('PROBABLE') || decision.includes('POSSIBLE');

  return (
    <div className={`relative bg-black rounded-lg overflow-hidden border ${
      dangerLabel ? 'border-red-500 alert-critical' :
      warningLabel ? 'border-yellow-500' :
      'border-bp-border'
    } ${className}`}>

      {/* Frame */}
      {frame ? (
        <img
          src={`data:image/jpeg;base64,${frame}`}
          alt="Live camera feed"
          className="w-full h-full object-contain"
          style={{ display: 'block' }}
        />
      ) : (
        <div className="flex items-center justify-center h-full min-h-48 text-bp-muted">
          {connected ? (
            <div className="text-center">
              <div className="text-4xl mb-2">◎</div>
              <div className="text-sm">{cam?.online === false ? 'CAMERA OFFLINE' : 'Waiting for frame...'}</div>
            </div>
          ) : (
            <div className="text-center">
              <div className="text-4xl mb-2 text-bp-danger">✕</div>
              <div className="text-sm text-bp-danger">BACKEND OFFLINE</div>
            </div>
          )}
        </div>
      )}

      {/* Top-left overlays */}
      {showOverlay && (
        <div className="absolute top-2 left-2 flex flex-col gap-1">
          <div className="live-badge text-xs font-semibold uppercase tracking-wider">LIVE</div>
          {cam?.resolution && (
            <span className="bg-black/70 text-bp-muted text-xs px-2 py-0.5 rounded mono">
              {cam.resolution}
            </span>
          )}
        </div>
      )}

      {/* Top-right diagnostics */}
      {showOverlay && frame && (
        <div className="absolute top-2 right-2 flex flex-col gap-1 items-end">
          <span className="bg-black/70 text-bp-accent text-xs px-2 py-0.5 rounded mono">
            {fps.toFixed(1)} fps
          </span>
          <span className="bg-black/70 text-bp-dim text-xs px-2 py-0.5 rounded mono">
            {latency.toFixed(0)}ms
          </span>
        </div>
      )}

      {/* Bottom threat label */}
      {showOverlay && decision && (
        <div className={`absolute bottom-0 left-0 right-0 px-3 py-2 text-xs font-semibold uppercase tracking-wider ${
          dangerLabel ? 'bg-red-900/80 text-red-200' :
          warningLabel ? 'bg-yellow-900/80 text-yellow-200' :
          'bg-black/60 text-bp-muted'
        }`}>
          ⚡ {decision}
        </div>
      )}

      {/* Camera offline overlay */}
      {cam?.online === false && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60">
          <div className="text-center">
            <div className="text-red-400 text-5xl mb-2">⊘</div>
            <div className="text-red-300 font-semibold">CAMERA OFFLINE</div>
            <div className="text-bp-muted text-xs mt-1">{cam.error}</div>
          </div>
        </div>
      )}
    </div>
  );
}
