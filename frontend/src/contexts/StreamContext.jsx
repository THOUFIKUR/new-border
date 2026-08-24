import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { createStreamSocket } from '../services/api';

const StreamCtx = createContext(null);

export function StreamProvider({ children }) {
  const [streamData, setStreamData] = useState(null);
  const [connected, setConnected]   = useState(false);
  const socketRef = useRef(null);

  const connect = useCallback(() => {
    if (socketRef.current) return;
    const { ws, disconnect } = createStreamSocket(
      (data) => { setStreamData(data); setConnected(true); },
      () => { setConnected(false); socketRef.current = null; setTimeout(connect, 3000); }
    );
    socketRef.current = { ws, disconnect };
  }, []);

  useEffect(() => {
    connect();
    return () => { socketRef.current?.disconnect(); socketRef.current = null; };
  }, [connect]);

  return (
    <StreamCtx.Provider value={{ streamData, connected }}>
      {children}
    </StreamCtx.Provider>
  );
}

export const useStream = () => useContext(StreamCtx);
