'use client';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { ConnectionStatus } from '@/types';

interface StatusIndicatorProps {
  status: ConnectionStatus;
  compact?: boolean;
}

export function StatusIndicator({ status, compact = false }: StatusIndicatorProps) {
  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500 animate-pulse';
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

  // Compact mode: just the colored dot with tooltip
  if (compact) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className={`h-2 w-2 rounded-full shrink-0 ${getStatusColor()}`} />
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p>{getStatusText()}</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  // Full mode: badge with dot and text
  return (
    <Badge variant="outline" className="gap-1.5 text-xs px-1.5 sm:px-2.5">
      <span className={`h-2 w-2 rounded-full ${getStatusColor()}`} />
      <span className="hidden sm:inline">{getStatusText()}</span>
    </Badge>
  );
}
