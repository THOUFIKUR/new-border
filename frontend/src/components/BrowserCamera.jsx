// BorderPulse — Browser Camera Streamer & Local Live Preview Component
// Captures user's laptop/browser webcam, displays live local preview on Vercel frontend,
// and streams frames to backend FastAPI/YOLO service for AI processing.

import { useEffect, useRef, useState, useCallback } from 'react';
import { sendCameraFrame } from '../services/api';

export default function BrowserCamera({
  camId = 'cam_01',
  autoStart = true,
  onActiveChange,
  backendFrame = null,
}) {
  const [cameraState, setCameraState] = useState('UNINITIALIZED'); // UNINITIALIZED | REQUESTING | CONNECTED | PLAYING | ERROR
  const [errorMsg, setErrorMsg] = useState(null);
  const [debugInfo, setDebugInfo] = useState('');

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const isSendingRef = useRef(false);
  const isMountedRef = useRef(true);

  // Attach MediaStream to <video> DOM element and invoke play()
  const attachAndPlayStream = useCallback(async (mediaStream) => {
    const video = videoRef.current;
    if (!video || !mediaStream) {
      console.warn('[BROWSER_CAM] Video DOM element or MediaStream unavailable for attachment');
      return false;
    }

    try {
      console.log('[BROWSER_CAM] Attaching stream to videoRef.current.srcObject...');
      video.srcObject = mediaStream;

      const playPromise = video.play();
      if (playPromise !== undefined) {
        await playPromise;
      }
      console.log('[BROWSER_CAM] video.play() resolved successfully. Local webcam video is playing.');
      if (isMountedRef.current) {
        setCameraState('PLAYING');
      }
      return true;
    } catch (err) {
      console.error('[BROWSER_CAM] Exception during video.play():', err);
      if (isMountedRef.current) {
        setErrorMsg(`Video playback error: ${err.message || err}`);
        setCameraState('ERROR');
      }
      return false;
    }
  }, []);

  // Main webcam initialization logic
  const startWebcam = useCallback(async () => {
    if (typeof window !== 'undefined' && !window.isSecureContext) {
      console.error('[BROWSER_CAM] Security Error: Window is not in a secure context (HTTPS required)');
      setErrorMsg('HTTPS security context required for browser camera access.');
      setCameraState('ERROR');
      return;
    }

    if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      console.error('[BROWSER_CAM] API Error: navigator.mediaDevices.getUserMedia is not supported');
      setErrorMsg('Camera API (getUserMedia) is not supported by this browser.');
      setCameraState('ERROR');
      return;
    }

    // Stop existing stream if any
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => {
        try { t.stop(); } catch {}
      });
      streamRef.current = null;
    }

    if (isMountedRef.current) {
      setCameraState('REQUESTING');
      setErrorMsg(null);
    }
    console.log('[BROWSER_CAM] Requesting getUserMedia({ video: true, audio: false })...');

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
        audio: false,
      });

      if (!isMountedRef.current) {
        console.log('[BROWSER_CAM] Component unmounted while waiting for getUserMedia. Stopping tracks.');
        mediaStream.getTracks().forEach((t) => t.stop());
        return;
      }

      // Log MediaStream diagnostics
      const tracks = mediaStream.getVideoTracks();
      const track = tracks[0];
      const settings = track ? track.getSettings() : {};
      console.log('[BROWSER_CAM] getUserMedia SUCCESS:', {
        active: mediaStream.active,
        trackCount: tracks.length,
        readyState: track?.readyState,
        enabled: track?.enabled,
        muted: track?.muted,
        settings,
      });

      setDebugInfo(`${settings.width || 640}x${settings.height || 480}`);
      streamRef.current = mediaStream;
      if (isMountedRef.current) {
        setCameraState('CONNECTED');
      }
      onActiveChange?.(true);

      // Attach stream to video element
      await attachAndPlayStream(mediaStream);
    } catch (err) {
      console.error('[BROWSER_CAM] getUserMedia ERROR:', err);
      if (!isMountedRef.current) return;

      let msg = 'Camera access failed.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        msg = 'Camera permission denied. Please allow camera access in your browser address bar.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        msg = 'No physical webcam device found on this system.';
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        msg = 'Camera is currently locked by another application.';
      } else {
        msg = err.message || 'Webcam initialization failed.';
      }
      setErrorMsg(msg);
      setCameraState('ERROR');
      onActiveChange?.(false);
    }
  }, [attachAndPlayStream, onActiveChange]);

  // Stop webcam cleanup
  const stopWebcam = useCallback(() => {
    console.log('[BROWSER_CAM] Stopping webcam stream and resetting timers...');
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try { track.stop(); } catch {}
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (isMountedRef.current) {
      setCameraState('UNINITIALIZED');
    }
    onActiveChange?.(false);
  }, [onActiveChange]);

  // Initial mount / unmount lifecycle
  useEffect(() => {
    isMountedRef.current = true;
    if (autoStart) {
      startWebcam();
    }
    return () => {
      isMountedRef.current = false;
      stopWebcam();
    };
  }, [autoStart, startWebcam, stopWebcam]);

  // Frame capture loop tick — posts JPEG base64 frames to backend for YOLO AI inference
  const captureAndSend = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2 || isSendingRef.current) return;

    try {
      isSendingRef.current = true;
      const ctx = canvas.getContext('2d');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const b64Image = canvas.toDataURL('image/jpeg', 0.65);
      await sendCameraFrame(b64Image, camId);
    } catch (e) {
      console.debug('[BROWSER_CAM] Frame send exception:', e);
    } finally {
      isSendingRef.current = false;
    }
  }, [camId]);

  useEffect(() => {
    if (cameraState === 'PLAYING') {
      timerRef.current = setInterval(captureAndSend, 100); // 10 FPS
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [cameraState, captureAndSend]);

  return (
    <div className="relative w-full h-full min-h-[300px] flex items-center justify-center bg-black overflow-hidden border border-bp-border">
      {/* Hidden Canvas for encoding frame to send to YOLO backend */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* 
        CRITICAL: The <video> element MUST ALWAYS BE MOUNTED IN THE DOM.
        Never conditionally unmount this <video> tag when backendFrame is truthy,
        otherwise the videoRef and MediaStream srcObject will be lost!
      */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        onLoadedMetadata={() => {
          console.log('[BROWSER_CAM] Event: onLoadedMetadata');
          if (streamRef.current && videoRef.current) {
            videoRef.current.play().catch((e) => console.warn('[BROWSER_CAM] play() on metadata:', e));
          }
        }}
        onCanPlay={() => console.log('[BROWSER_CAM] Event: onCanPlay')}
        onPlaying={() => {
          console.log('[BROWSER_CAM] Event: onPlaying');
          if (isMountedRef.current) setCameraState('PLAYING');
        }}
        onError={(e) => {
          console.error('[BROWSER_CAM] Video element onError:', e);
          if (isMountedRef.current) {
            setErrorMsg('Video playback element error.');
            setCameraState('ERROR');
          }
        }}
        className={`w-full h-full object-contain ${backendFrame ? 'hidden' : 'block'}`}
      />

      {/* Overlay backend AI annotated frame if received from Render WebSocket */}
      {backendFrame && (
        <img
          src={`data:image/jpeg;base64,${backendFrame}`}
          alt="YOLO AI Annotated Feed"
          className="w-full h-full object-contain z-10"
        />
      )}

      {/* Status Badge Overlay */}
      <div className="absolute top-2 left-2 z-20 flex items-center gap-2 pointer-events-none">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
          cameraState === 'PLAYING' ? 'bg-green-500/90 text-black' :
          cameraState === 'CONNECTED' ? 'bg-blue-500/90 text-white' :
          cameraState === 'REQUESTING' ? 'bg-yellow-500/90 text-black animate-pulse' :
          cameraState === 'ERROR' ? 'bg-red-500/90 text-white' :
          'bg-gray-700/90 text-gray-300'
        }`}>
          CAMERA: {cameraState}
        </span>
        {debugInfo && (
          <span className="bg-black/80 text-bp-muted text-[10px] px-1.5 py-0.5 rounded mono">
            {debugInfo}
          </span>
        )}
      </div>

      {/* Visible Error Overlay */}
      {cameraState === 'ERROR' && errorMsg && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/90 p-4 text-center z-30">
          <div className="max-w-md bg-red-950/90 border border-red-500/60 rounded-lg p-6 text-red-200 shadow-2xl">
            <div className="text-4xl mb-3">📷</div>
            <div className="text-lg font-bold mb-2">Webcam Initialization Failed</div>
            <div className="text-xs text-red-300 mb-5 leading-relaxed">{errorMsg}</div>
            <button
              onClick={() => startWebcam()}
              className="px-5 py-2.5 bg-red-600 hover:bg-red-500 text-white font-bold text-xs rounded-md shadow-md transition-all uppercase tracking-wider"
            >
              Retry Camera Connection
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
