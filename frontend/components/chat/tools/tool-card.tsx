'use client';

import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn, formatTime } from '@/lib/utils';
import { ToolStatusBadge, type ToolStatus } from './tool-status-badge';

interface ToolCardProps {
  /** Tool name displayed in the header */
  toolName: string;
  /** Tool icon component */
  ToolIcon: LucideIcon;
  /** Border and icon color (CSS color value) */
  color?: string;
  /** Current execution status */
  status: ToolStatus;
  /** Whether the card is expanded */
  isExpanded: boolean;
  /** Toggle expansion callback */
  onToggle: () => void;
  /** Summary text shown when collapsed */
  summary?: string;
  /** Optional timestamp to display */
  timestamp?: Date;
  /** Whether the tool is currently running (adds animation) */
  isRunning?: boolean;
  /** Card content (shown when expanded) */
  children?: ReactNode;
  /** Additional className for the outer container */
  className?: string;
  /** Accessibility label for the card */
  ariaLabel?: string;
  /** Unique ID for accessibility controls */
  toolId?: string;
}

/**
 * Base card wrapper used by all tool types.
 * Provides consistent styling, collapsible header, and status indicator.
 */
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

  // Generate aria-label if not provided
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
      {/* Icon column */}
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

      {/* Content column */}
      <div className="min-w-0 flex-1" aria-live="polite">
        <Card
          className="overflow-hidden rounded-lg shadow-sm w-full md:max-w-2xl bg-muted/30 border-l-2"
          style={{ borderLeftColor: borderColor }}
        >
          {/* Collapsible header */}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start rounded-none border-b border-border/50 px-2 sm:px-3 py-2 text-xs hover:bg-muted/50 h-auto min-h-[40px] sm:min-h-[36px]"
            onClick={onToggle}
            aria-expanded={isExpanded}
            aria-controls={detailsId}
          >
            <div className="flex items-center gap-2 w-full">
              {/* Chevron */}
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              )}

              {/* Tool name */}
              <span className="font-medium text-foreground">{toolName}</span>

              {/* Summary (when collapsed) */}
              {!isExpanded && summary && (
                <>
                  <span className="text-muted-foreground/60">:</span>
                  <span className="text-muted-foreground/80 font-mono text-xs sm:text-[11px] truncate">
                    {summary}
                  </span>
                </>
              )}

              {/* Status indicator (right side) */}
              <span className="ml-auto">
                <ToolStatusBadge status={status} />
              </span>
            </div>
          </Button>

          {/* Expanded content with smooth transition */}
          <div
            className={cn(
              "grid transition-all duration-200 ease-out",
              isExpanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            )}
          >
            <div className="overflow-hidden">
              <div className="bg-background/50" id={detailsId}>
                {children}
              </div>
            </div>
          </div>
        </Card>

        {/* Timestamp (hover only) */}
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
  /** Tool name displayed in the header */
  toolName: string;
  /** Tool icon component */
  ToolIcon: LucideIcon;
  /** Border and icon color (CSS color value) */
  color?: string;
  /** Whether the tool is currently running */
  isRunning?: boolean;
  /** Optional timestamp */
  timestamp?: Date;
  /** Header content (right side) */
  headerContent?: ReactNode;
  /** Card content (always visible) */
  children?: ReactNode;
  /** Additional className */
  className?: string;
  /** Accessibility label for the card */
  ariaLabel?: string;
}

/**
 * Non-collapsible card variant for tools that should always show content.
 * Used for TodoWrite, EnterPlanMode, etc.
 */
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
      {/* Icon column */}
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

      {/* Content column */}
      <div className="min-w-0 flex-1" aria-live="polite">
        <Card
          className="overflow-hidden rounded-lg shadow-sm w-full md:max-w-2xl bg-muted/30 border-l-2"
          style={{ borderLeftColor: borderColor }}
        >
          {/* Header (non-clickable) */}
          <div className="px-3 py-2 border-b border-border/50">
            <div className="flex items-center gap-2">
              <span className="font-medium text-xs text-foreground">{toolName}</span>
              {headerContent}
            </div>
          </div>

          {/* Content (always visible) */}
          {children && <div className="bg-background/50">{children}</div>}
        </Card>

        {/* Timestamp (hover only) */}
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
