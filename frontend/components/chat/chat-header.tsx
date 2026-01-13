'use client';

import { Button } from '@/components/ui/button';
import { Trash2, RefreshCw, Settings, Hash, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatHeaderProps {
  sessionId?: string | null;
  turnCount?: number;
  isStreaming?: boolean;
  onNewSession?: () => void;
  onClear?: () => void;
  className?: string;
}

export function ChatHeader({
  sessionId,
  turnCount = 0,
  isStreaming = false,
  onNewSession,
  onClear,
  className,
}: ChatHeaderProps) {
  // Format session ID for display (truncate if too long)
  const displaySessionId = sessionId
    ? sessionId.length > 12
      ? `${sessionId.slice(0, 8)}...`
      : sessionId
    : 'New Session';

  return (
    <header
      className={cn(
        'flex items-center justify-between px-4 py-3',
        'border-b border-[var(--claude-border)]',
        'bg-[var(--claude-background)]',
        className
      )}
    >
      {/* Left side: Session info */}
      <div className="flex items-center gap-4">
        {/* Session ID */}
        <div className="flex items-center gap-2 text-sm">
          <Hash className="h-4 w-4 text-[var(--claude-foreground-muted)]" />
          <span
            className="font-mono text-[var(--claude-foreground-muted)]"
            title={sessionId || 'No active session'}
          >
            {displaySessionId}
          </span>
        </div>

        {/* Turn count */}
        <div className="flex items-center gap-1.5 text-sm text-[var(--claude-foreground-muted)]">
          <MessageSquare className="h-4 w-4" />
          <span>{turnCount} {turnCount === 1 ? 'turn' : 'turns'}</span>
        </div>

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--claude-primary)] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--claude-primary)]" />
            </span>
            <span className="text-xs text-[var(--claude-primary)]">Streaming</span>
          </div>
        )}
      </div>

      {/* Right side: Actions */}
      <div className="flex items-center gap-2">
        {/* Clear conversation button */}
        {onClear && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            disabled={isStreaming}
            className="text-[var(--claude-foreground-muted)] hover:text-[var(--claude-foreground)]"
            title="Clear conversation"
          >
            <Trash2 className="h-4 w-4" />
            <span className="sr-only">Clear</span>
          </Button>
        )}

        {/* New session button */}
        {onNewSession && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onNewSession}
            disabled={isStreaming}
            className="text-[var(--claude-foreground-muted)] hover:text-[var(--claude-foreground)]"
            title="Start new session"
          >
            <RefreshCw className="h-4 w-4" />
            <span className="sr-only">New Session</span>
          </Button>
        )}
      </div>
    </header>
  );
}
