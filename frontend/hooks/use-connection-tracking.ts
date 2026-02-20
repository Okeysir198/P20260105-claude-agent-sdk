import { useState, useEffect, useCallback } from 'react';
import { useChatStore } from '@/lib/store/chat-store';

interface ConnectionTrackingState {
  wasConnected: boolean;
  reconnectAttempt: number;
  isReconnecting: boolean;
  handleManualReconnect: () => void;
}

export function useConnectionTracking(): ConnectionTrackingState {
  const connectionStatus = useChatStore((s) => s.connectionStatus);
  const [wasConnected, setWasConnected] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  useEffect(() => {
    if (connectionStatus === 'connected') {
      setWasConnected(true);
      setReconnectAttempt(0);
    } else if (connectionStatus === 'connecting' && wasConnected) {
      setReconnectAttempt((prev) => prev + 1);
    }
  }, [connectionStatus, wasConnected]);

  const isReconnecting = wasConnected && connectionStatus === 'connecting';

  const handleManualReconnect = useCallback(() => {
    window.location.reload();
  }, []);

  return {
    wasConnected,
    reconnectAttempt,
    isReconnecting,
    handleManualReconnect,
  };
}
