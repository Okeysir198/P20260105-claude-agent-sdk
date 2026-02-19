'use client';
import { Badge } from '@/components/ui/badge';
import type { ConnectionStatus } from '@/types';

interface StatusIndicatorProps {
  status: ConnectionStatus;
}

const STATUS_CONFIG: Record<ConnectionStatus, { color: string; label: string }> = {
  connected: { color: 'bg-green-500', label: 'Connected' },
  connecting: { color: 'bg-yellow-500', label: 'Connecting...' },
  error: { color: 'bg-red-500', label: 'Error' },
  disconnected: { color: 'bg-muted-foreground', label: 'Disconnected' },
};

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const { color, label } = STATUS_CONFIG[status] ?? STATUS_CONFIG.disconnected;

  return (
    <Badge variant="outline" className="gap-1.5 text-xs px-1.5 sm:px-2.5">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      <span className="hidden sm:inline">{label}</span>
    </Badge>
  );
}
