'use client';

import { Loader2, WifiOff, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ConnectionBannerProps {
  status: 'connecting' | 'disconnected' | 'reconnecting';
  reconnectAttempt?: number;
  maxAttempts?: number;
  onRetry?: () => void;
}

function getMessage(status: 'connecting' | 'disconnected' | 'reconnecting', reconnectAttempt?: number, maxAttempts?: number): string {
  if (status === 'connecting') {
    return 'Connecting to server...';
  }
  if (status === 'reconnecting') {
    return reconnectAttempt && maxAttempts
      ? `Connection lost. Reconnecting (${reconnectAttempt}/${maxAttempts})...`
      : 'Connection lost. Reconnecting...';
  }
  if (status === 'disconnected') {
    return 'You are currently offline';
  }
  return 'Connection issue detected';
}

export function ConnectionBanner({ status, reconnectAttempt, maxAttempts, onRetry }: ConnectionBannerProps) {
  const isDisconnected = status === 'disconnected';

  return (
    <div className="flex items-center justify-between gap-3 border-b border-status-warning/30 bg-status-warning-bg px-4 py-2 text-sm text-status-warning-fg">
      <div className="flex items-center gap-2">
        {isDisconnected ? <WifiOff className="h-4 w-4" /> : <Loader2 className="h-4 w-4 animate-spin" />}
        <span>{getMessage(status, reconnectAttempt, maxAttempts)}</span>
      </div>
      {isDisconnected && onRetry && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onRetry}
          className="h-7 px-2 text-status-warning-fg hover:text-status-warning"
        >
          <RefreshCw className="mr-1 h-3 w-3" />
          Retry
        </Button>
      )}
    </div>
  );
}
