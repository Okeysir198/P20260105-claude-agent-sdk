'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WebSocketEvent {
  type: 'ready' | 'session_id' | 'text_delta' | 'tool_use' | 'tool_result' | 'done' | 'error';
  [key: string]: unknown;
}

interface UseWebSocketOptions {
  onMessage: (event: WebSocketEvent) => void;
  onError?: (error: Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface UseWebSocketReturn {
  state: ConnectionState;
  connect: (url: string) => void;
  disconnect: () => void;
  send: (data: object) => boolean;
  isReady: boolean;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const { onMessage, onError, onConnect, onDisconnect } = options;

  const [state, setState] = useState<ConnectionState>('disconnected');
  const [isReady, setIsReady] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const optionsRef = useRef(options);

  // Keep options ref current to avoid stale closures
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState('disconnected');
    setIsReady(false);
  }, []);

  const connect = useCallback((url: string) => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setState('connecting');
    setIsReady(false);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setState('connected');
        optionsRef.current.onConnect?.();
      };

      ws.onclose = () => {
        setState('disconnected');
        setIsReady(false);
        optionsRef.current.onDisconnect?.();
        wsRef.current = null;
      };

      ws.onerror = () => {
        setState('error');
        setIsReady(false);
        optionsRef.current.onError?.(new Error('WebSocket connection failed'));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;

          // Set ready flag when server sends ready event
          if (data.type === 'ready') {
            setIsReady(true);
          }

          optionsRef.current.onMessage(data);
        } catch (err) {
          optionsRef.current.onError?.(
            new Error(`Failed to parse message: ${event.data}`)
          );
        }
      };
    } catch (err) {
      setState('error');
      optionsRef.current.onError?.(
        err instanceof Error ? err : new Error('Failed to create WebSocket')
      );
    }
  }, []);

  const send = useCallback((data: object): boolean => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      wsRef.current.send(JSON.stringify(data));
      return true;
    } catch {
      return false;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  return {
    state,
    connect,
    disconnect,
    send,
    isReady,
  };
}
