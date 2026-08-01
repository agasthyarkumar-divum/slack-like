import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { PropsWithChildren } from "react";

import { API_BASE_URL } from "@/lib/api/client";
import { tokenStorage } from "@/lib/api/tokenStorage";
import { useAuth } from "@/lib/auth/AuthContext";

type WSEvent = { event: string; data: Record<string, unknown> };
type Handler = (data: Record<string, unknown>) => void;

type WSContextValue = {
  isConnected: boolean;
  subscribe: (eventName: string, handler: Handler) => () => void;
  send: (event: string, data: Record<string, unknown>) => void;
};

const WSContext = createContext<WSContextValue | null>(null);

function toWebSocketUrl(baseUrl: string): string {
  return baseUrl.replace(/^http/, "ws") + "/ws";
}

const RECONNECT_DELAY_MS = 4000;

export function WSProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, Set<Handler>>>(new Map());
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    if (!user) return;

    let cancelled = false;

    async function connect() {
      const token = await tokenStorage.getAccessToken();
      if (!token || cancelled) return;

      const socket = new WebSocket(`${toWebSocketUrl(API_BASE_URL)}?token=${encodeURIComponent(token)}`);
      socketRef.current = socket;

      socket.onopen = () => {
        if (mountedRef.current) setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const parsed: WSEvent = JSON.parse(event.data);
          const handlers = handlersRef.current.get(parsed.event);
          handlers?.forEach((handler) => handler(parsed.data));
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        if (!cancelled) {
          reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [user]);

  useEffect(
    () => () => {
      mountedRef.current = false;
    },
    []
  );

  function subscribe(eventName: string, handler: Handler) {
    if (!handlersRef.current.has(eventName)) handlersRef.current.set(eventName, new Set());
    handlersRef.current.get(eventName)!.add(handler);
    return () => handlersRef.current.get(eventName)?.delete(handler);
  }

  function send(event: string, data: Record<string, unknown>) {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ event, data }));
    }
  }

  return (
    <WSContext.Provider value={{ isConnected, subscribe, send }}>{children}</WSContext.Provider>
  );
}

export function useWS(): WSContextValue {
  const ctx = useContext(WSContext);
  if (!ctx) throw new Error("useWS must be used within a WSProvider");
  return ctx;
}
