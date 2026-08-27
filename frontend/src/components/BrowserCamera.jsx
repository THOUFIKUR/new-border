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
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const [isLive, setIsLive] = useState(false);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const isSendingRef = useRef(false);

  // Start webcam stream
  const startWebcam = useCallback(async () => {
    if (streamRef.current) return; // Already running

    setError(null);
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = mediaStream;
      setStream(mediaStream);
      setIsLive(true);
      onActiveChange?.(true);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.play().catch((err) => {
          console.warn('[BROWSER_CAM] Autoplay exception:', err);
        });
      }
    } catch (err) {
      console.error('[BROWSER_CAM] Error accessing webcam:', err);
      let errMsg = 'Webcam access denied or unavailable.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errMsg = 'Camera permission denied. Please allow camera access in browser settings.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        errMsg = 'No physical camera device found on this system.';
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        errMsg = 'Camera is currently in use by another application.';
      }
      setError(errMsg);
      setIsLive(false);
      onActiveChange?.(false);
    }
  }, [onActiveChange]);

  // Stop webcam stream & clean up tracks
  const stopWebcam = useCallback(() => {
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
    setStream(null);
    setIsLive(false);
    onActiveChange?.(false);
  }, [onActiveChange]);

  // Attach stream when video element or stream state changes
  useEffect(() => {
    if (stream && videoRef.current && videoRef.current.srcObject !== stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch((err) => console.warn('[BROWSER_CAM] Play error:', err));
    }
  }, [stream]);

  // Start / stop lifecycle
  useEffect(() => {
    let isMounted = true;
    if (autoStart) {
      startWebcam();
    }
    return () => {
      isMounted = false;
      stopWebcam();
    };
  }, [autoStart, startWebcam, stopWebcam]);

  // Frame capture loop tick — posts frames to backend for YOLO processing
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
    if (isLive) {
      timerRef.current = setInterval(captureAndSend, 100); // 10 FPS
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isLive, captureAndSend]);

  return (
    <div className="relative w-full h-full flex items-center justify-center bg-black overflow-hidden">
      {/* Hidden Canvas for encoding frame to send to YOLO backend */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* Backend YOLO Annotated Frame (if available from Render WebSocket) */}
      {backendFrame ? (
        <img
          src={`data:image/jpeg;base64,${backendFrame}`}
          alt="YOLO AI Annotated Feed"
          className="w-full h-full object-contain"
        />
      ) : (
        /* Direct Local Live Video Element (Instant feedback on Vercel) */
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-contain"
        />
      )}

      {/* Error Banner / Overlay */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/90 p-4 text-center z-30">
          <div className="max-w-md bg-red-950/80 border border-red-500/50 rounded-lg p-6 text-red-200 shadow-xl">
            <div className="text-4xl mb-3">📷</div>
            <div className="text-lg font-bold mb-2">Webcam Error</div>
            <div className="text-xs text-red-300 mb-4">{error}</div>
            <button
              onClick={() => { setError(null); startWebcam(); }}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-bold text-xs rounded transition-all"
            >
              Retry Camera Access
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
