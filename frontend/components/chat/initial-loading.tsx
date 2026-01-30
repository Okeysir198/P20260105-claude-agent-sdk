'use client';

import { Loader2 } from 'lucide-react';

interface InitialLoadingProps {
  status: 'connecting' | 'disconnected';
}

export function InitialLoading({ status }: InitialLoadingProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">
        {status === 'connecting' ? 'Connecting to server...' : 'Waiting for connection...'}
      </p>
    </div>
  );
}
