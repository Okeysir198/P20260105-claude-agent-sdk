'use client';

import { WifiOff, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ConnectionErrorProps {
  onRetry: () => void;
}

export function ConnectionError({ onRetry }: ConnectionErrorProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
      <div className="flex items-center gap-2 text-destructive">
        <WifiOff className="h-8 w-8" />
        <h2 className="text-lg font-semibold">Connection Error</h2>
      </div>
      <p className="max-w-md text-center text-sm text-muted-foreground">
        Unable to establish a connection to the chat server. This could be due to network issues or the server being temporarily unavailable.
      </p>
      <div className="flex flex-col items-center gap-2">
        <Button onClick={onRetry}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Reconnect
        </Button>
        <p className="text-xs text-muted-foreground">
          If the problem persists, try refreshing the page or checking your network connection.
        </p>
      </div>
    </div>
  );
}
