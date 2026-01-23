'use client';
import { Badge } from '@/components/ui/badge';
import type { ConnectionStatus } from '@/types';

interface StatusIndicatorProps {
  status: ConnectionStatus;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-muted-foreground';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return 'Error';
      default:
        return 'Disconnected';
    }
  };

  return (
    <Badge variant="outline" className="gap-1.5 text-xs">
      <span className={`h-2 w-2 rounded-full ${getStatusColor()}`} />
      {getStatusText()}
    </Badge>
  );
}
