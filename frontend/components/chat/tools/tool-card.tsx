'use client';

import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn, formatTime } from '@/lib/utils';
import { ToolStatusBadge, type ToolStatus } from './tool-status-badge';

interface ToolCardProps {
  toolName: string;
  ToolIcon: LucideIcon;
  color?: string;
  status: ToolStatus;
  isExpanded: boolean;
  onToggle: () => void;
  summary?: string;
  timestamp?: Date;
  isRunning?: boolean;
  children?: ReactNode;
  className?: string;
  ariaLabel?: string;
  toolId?: string;
}

export function ToolCard({
  toolName,
  ToolIcon,
  color,
  status,
  isExpanded,
  onToggle,
  summary,
  timestamp,
  isRunning = false,
  children,
  className,
  ariaLabel,
  toolId,
}: ToolCardProps) {
  const borderColor = color || 'hsl(var(--border))';
  const iconColor = color || 'hsl(var(--muted-foreground))';

  const computedAriaLabel = ariaLabel || (() => {
    const statusText = status === 'running' ? 'running' : status === 'completed' ? 'completed' : status === 'error' ? 'failed' : status === 'interrupted' ? 'interrupted' : 'pending';
    const summaryText = summary ? `: ${summary}` : '';
    return `${toolName} tool ${statusText}${summaryText}`;
  })();

  const detailsId = toolId || `tool-details-${toolName}-${Date.now()}`;

  return (
    <div
      className={cn('group flex gap-2 sm:gap-3 py-1.5 px-2 sm:px-4', className)}
      role="article"
      aria-label={computedAriaLabel}
    >
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border',
          isRunning && 'animate-pulse'
        )}
        style={{ color: iconColor }}
        aria-hidden="true"
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ToolIcon className="h-3.5 w-3.5" />
        )}
      </div>

      <div className="min-w-0 flex-1 overflow-hidden" aria-live="polite">
        <Card
          className="overflow-hidden rounded-lg shadow-sm w-full md:max-w-2xl max-w-full bg-muted/30 border-l-2"
          style={{ borderLeftColor: borderColor }}
        >
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start rounded-none border-b border-border/50 px-2 sm:px-3 py-2 text-xs hover:bg-muted/50 h-auto min-h-[40px] sm:min-h-[36px]"
            onClick={onToggle}
            aria-expanded={isExpanded}
            aria-controls={detailsId}
          >
            <div className="flex items-center gap-1.5 sm:gap-2 w-full min-w-0">
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              )}

              <div className="flex items-center gap-1.5 min-w-0 overflow-hidden">
                <span className="font-medium text-foreground truncate">{toolName}</span>

                {!isExpanded && summary && (
                  <>
                    <span className="text-muted-foreground/60 shrink-0">:</span>
                    <span className="text-muted-foreground/80 font-mono text-xs sm:text-[11px] truncate">
                      {summary}
                    </span>
                  </>
                )}
              </div>

              <span className="ml-auto shrink-0">
                <ToolStatusBadge status={status} />
              </span>
            </div>
          </Button>

          <div
            className={cn(
              "grid transition-all duration-200 ease-out",
              isExpanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            )}
          >
            <div className="overflow-hidden">
              <div className="bg-background/50 overflow-x-auto" id={detailsId}>
                {children}
              </div>
            </div>
          </div>
        </Card>

        {timestamp && (
          <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-xs sm:text-[11px] text-muted-foreground">
              {formatTime(timestamp)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

interface NonCollapsibleToolCardProps {
  toolName: string;
  ToolIcon: LucideIcon;
  color?: string;
  isRunning?: boolean;
  timestamp?: Date;
  headerContent?: ReactNode;
  children?: ReactNode;
  className?: string;
  ariaLabel?: string;
}

export function NonCollapsibleToolCard({
  toolName,
  ToolIcon,
  color,
  isRunning = false,
  timestamp,
  headerContent,
  children,
  className,
  ariaLabel,
}: NonCollapsibleToolCardProps) {
  const borderColor = color || 'hsl(var(--border))';
  const iconColor = color || 'hsl(var(--muted-foreground))';

  return (
    <div
      className={cn('group flex gap-2 sm:gap-3 py-1.5 px-2 sm:px-4', className)}
      role="article"
      aria-label={ariaLabel}
    >
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border',
          isRunning && 'animate-pulse'
        )}
        style={{ color: iconColor }}
        aria-hidden="true"
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ToolIcon className="h-3.5 w-3.5" />
        )}
      </div>

      <div className="min-w-0 flex-1 overflow-hidden" aria-live="polite">
        <Card
          className="overflow-hidden rounded-lg shadow-sm w-full md:max-w-2xl max-w-full bg-muted/30 border-l-2"
          style={{ borderLeftColor: borderColor }}
        >
          <div className="px-3 py-2 border-b border-border/50">
            <div className="flex items-center gap-2">
              <span className="font-medium text-xs text-foreground">{toolName}</span>
              {headerContent}
            </div>
          </div>

          {children && <div className="bg-background/50 overflow-hidden">{children}</div>}
        </Card>

        {timestamp && (
          <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-xs sm:text-[11px] text-muted-foreground">
              {formatTime(timestamp)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
