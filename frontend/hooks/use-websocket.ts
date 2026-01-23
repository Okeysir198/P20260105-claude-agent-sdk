'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { WebSocketManager } from '@/lib/websocket-manager';
import type { WebSocketEvent } from '@/types';

export function useWebSocket() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [error, setError] = useState<Error | null>(null);
  const wsManagerRef = useRef<WebSocketManager | null>(null);

  useEffect(() => {
    if (!wsManagerRef.current) {
      wsManagerRef.current = new WebSocketManager();
    }

    const manager = wsManagerRef.current;

    const unsubscribeStatus = manager.onStatus((newStatus) => {
      setStatus(newStatus);
    });

    const unsubscribeError = manager.onError((err) => {
      setError(err);
    });

    return () => {
      unsubscribeStatus();
      unsubscribeError();
    };
  }, []);

  const connect = useCallback((agentId: string | null, sessionId: string | null = null) => {
    setError(null);
    wsManagerRef.current?.connect(agentId, sessionId);
  }, []);

  const disconnect = useCallback(() => {
    wsManagerRef.current?.disconnect();
  }, []);

  const sendMessage = useCallback((content: string) => {
    wsManagerRef.current?.sendMessage(content);
  }, []);

  const onMessage = useCallback((callback: (event: WebSocketEvent) => void) => {
    return wsManagerRef.current?.onMessage(callback);
  }, []);

  const getReadyState = useCallback(() => {
    return wsManagerRef.current?.getReadyState() ?? WebSocket.CLOSED;
  }, []);

  return {
    status,
    error,
    connect,
    disconnect,
    sendMessage,
    onMessage,
    getReadyState,
  };
}
