'use client';

import { Loader2, CheckCircle2, AlertCircle, Clock, StopCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ToolStatus = 'running' | 'completed' | 'error' | 'pending' | 'interrupted';

interface ToolStatusBadgeProps {
  status: ToolStatus;
  duration?: number; // in milliseconds
  showLabel?: boolean;
  className?: string;
}

/**
 * Displays tool execution status with appropriate icon and optional label.
 */
export function ToolStatusBadge({
  status,
  duration,
  showLabel = true,
  className,
}: ToolStatusBadgeProps) {
  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.round(ms / 100) / 10;
    return `${seconds}s`;
  };

  const statusConfig = {
    running: {
      icon: <Loader2 className="h-4 w-4 animate-spin" />,
      label: 'Running',
      className: 'text-blue-500 animate-pulse',
    },
    completed: {
      icon: <CheckCircle2 className="h-4 w-4" />,
      label: duration ? formatDuration(duration) : 'Done',
      className: 'text-green-500',
    },
    error: {
      icon: <AlertCircle className="h-4 w-4" />,
      label: 'Error',
      className: 'text-destructive',
    },
    pending: {
      icon: <Clock className="h-3.5 w-3.5 animate-pulse" />,
      label: 'Pending',
      className: 'text-amber-500 animate-pulse',
    },
    interrupted: {
      icon: <StopCircle className="h-4 w-4" />,
      label: 'Interrupted',
      className: 'text-amber-500',
    },
  };

  const config = statusConfig[status];

  return (
    <span className={cn('flex items-center gap-1 shrink-0', config.className, className)}>
      {config.icon}
      {showLabel && (
        <span className="text-[10px] font-medium">{config.label}</span>
      )}
    </span>
  );
}

/**
 * Compact status indicator (icon only, useful for collapsed states)
 */
export function ToolStatusIcon({
  status,
  className,
}: {
  status: ToolStatus;
  className?: string;
}) {
  return <ToolStatusBadge status={status} showLabel={false} className={className} />;
}

/**
 * Animated running indicator with pulsing dot
 */
export function RunningIndicator({
  label = 'Running',
  color = 'hsl(var(--foreground))',
}: {
  label?: string;
  color?: string;
}) {
  return (
    <span className="text-xs text-muted-foreground flex items-center gap-1.5">
      <span className="relative flex h-2 w-2">
        <span
          className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
          style={{ backgroundColor: `${color}40` }}
        />
        <span
          className="relative inline-flex rounded-full h-2 w-2"
          style={{ backgroundColor: `${color}60` }}
        />
      </span>
      <span className="text-[11px]">{label}</span>
    </span>
  );
}
