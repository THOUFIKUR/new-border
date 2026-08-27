// BorderPulse — Live Camera Feed with detection overlays
import { useState } from 'react';
import { useStream } from '../contexts/StreamContext';
import BrowserCamera from './BrowserCamera';

export default function CameraFeed({ className = '', showOverlay = true, camId = 'cam_01' }) {
  const { streamData, connected } = useStream();
  const [useBrowserCam, setUseBrowserCam] = useState(false);
  const [isCamActive, setIsCamActive] = useState(false);

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

      {/* Main View Area: Either Browser Camera (Local/Render hybrid) OR Backend Hardware Stream */}
      {useBrowserCam ? (
        <BrowserCamera
          camId={camId}
          autoStart={true}
          onActiveChange={setIsCamActive}
          backendFrame={frame}
        />
      ) : frame ? (
        <img
          src={`data:image/jpeg;base64,${frame}`}
          alt="Live camera feed"
          className="w-full h-full object-contain"
          style={{ display: 'block' }}
        />
      ) : (
        <div className="flex items-center justify-center h-full min-h-48 text-bp-muted p-4">
          {connected ? (
            <div className="text-center space-y-3">
              <div className="text-4xl text-bp-dim">◎</div>
              <div className="text-sm font-semibold">
                {cam?.online === false ? 'PHYSICAL HARDWARE CAMERA OFFLINE' : 'Waiting for backend frame...'}
              </div>
              <button
                onClick={() => setUseBrowserCam(true)}
                className="px-4 py-2 bg-bp-accent/20 border border-bp-accent text-bp-accent font-bold text-xs rounded hover:bg-bp-accent/30 transition-all flex items-center justify-center gap-2 mx-auto"
              >
                <span>📷</span> START LAPTOP / BROWSER CAMERA
              </button>
            </div>
          ) : (
            <div className="text-center space-y-3">
              <div className="text-4xl text-bp-danger">✕</div>
              <div className="text-sm text-bp-danger font-semibold">RENDER BACKEND OFFLINE</div>
              <button
                onClick={() => setUseBrowserCam(true)}
                className="px-4 py-2 bg-bp-accent/20 border border-bp-accent text-bp-accent font-bold text-xs rounded hover:bg-bp-accent/30 transition-all flex items-center justify-center gap-2 mx-auto"
              >
                <span>📷</span> USE BROWSER WEBCAM OFFLINE
              </button>
            </div>
          )}
        </div>
      )}

      {/* Top-left overlays */}
      {showOverlay && (
        <div className="absolute top-2 left-2 flex flex-col gap-1 z-10 pointer-events-none">
          <div className="flex items-center gap-1.5">
            <div className="live-badge text-xs font-semibold uppercase tracking-wider">LIVE</div>
            {useBrowserCam && (
              <span className="bg-bp-accent/80 text-black text-[10px] font-bold px-1.5 py-0.5 rounded uppercase">
                {frame ? 'BROWSER WEBCAM (AI ANNOTATED)' : 'BROWSER WEBCAM (LOCAL LIVE)'}
              </span>
            )}
          </div>
          {cam?.resolution && (
            <span className="bg-black/70 text-bp-muted text-xs px-2 py-0.5 rounded mono">
              {cam.resolution}
            </span>
          )}
        </div>
      )}

      {/* Top-right diagnostics & camera switch button */}
      {showOverlay && (
        <div className="absolute top-2 right-2 flex flex-col gap-1 items-end z-20">
          {(frame || useBrowserCam) && (
            <>
              <span className="bg-black/70 text-bp-accent text-xs px-2 py-0.5 rounded mono">
                {fps > 0 ? `${fps.toFixed(1)} fps` : 'LIVE'}
              </span>
              {latency > 0 && (
                <span className="bg-black/70 text-bp-dim text-xs px-2 py-0.5 rounded mono">
                  {latency.toFixed(0)}ms
                </span>
              )}
            </>
          )}
          <button
            onClick={() => setUseBrowserCam(!useBrowserCam)}
            title={useBrowserCam ? "Switch to backend physical hardware camera" : "Use browser webcam"}
            className={`text-[10px] font-bold px-2 py-0.5 rounded border transition-all ${
              useBrowserCam
                ? 'bg-bp-accent/30 border-bp-accent text-bp-accent hover:bg-bp-accent/40'
                : 'bg-black/70 border-bp-border text-bp-dim hover:text-bp-text'
            }`}
          >
            {useBrowserCam ? '📷 BROWSER CAM ACTIVE' : '📷 WEBCAM STREAM'}
          </button>
        </div>
      )}

      {/* Bottom threat label */}
      {showOverlay && decision && (
        <div className={`absolute bottom-0 left-0 right-0 px-3 py-2 text-xs font-semibold uppercase tracking-wider z-10 ${
          dangerLabel ? 'bg-red-900/80 text-red-200' :
          warningLabel ? 'bg-yellow-900/80 text-yellow-200' :
          'bg-black/60 text-bp-muted'
        }`}>
          ⚡ {decision}
        </div>
      )}

      {/* Camera offline overlay (only when browser camera is not enabled and no frame) */}
      {cam?.online === false && !useBrowserCam && !frame && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-20">
          <div className="text-center p-4">
            <div className="text-yellow-400 text-4xl mb-2">📷</div>
            <div className="text-yellow-300 font-bold text-sm">NO PHYSICAL HARDWARE CAMERA DETECTED</div>
            <div className="text-bp-muted text-xs mt-1 mb-4">{cam?.error || 'Render Cloud Instance (No USB Cam)'}</div>
            <button
              onClick={() => setUseBrowserCam(true)}
              className="px-4 py-2 bg-bp-green/20 border border-bp-green text-bp-green font-bold text-xs rounded hover:bg-bp-green/30 transition-all flex items-center justify-center gap-2 mx-auto"
            >
              <span>📷</span> START BROWSER WEBCAM STREAM
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
