'use client';

import { useSessions } from '@/hooks/use-sessions';
import { SessionItem } from './session-item';
import { NewSessionButton } from './new-session-button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { MessageSquare, RefreshCw, ChevronLeft, ChevronRight, AlertCircle } from 'lucide-react';

interface SessionSidebarProps {
  currentSessionId?: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
  className?: string;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

/**
 * Loading skeleton for the session list.
 */
function SessionListSkeleton() {
  return (
    <div className="space-y-2 p-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex items-center gap-3 p-2">
          <Skeleton className="w-8 h-8 rounded-md" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Empty state when no sessions exist.
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center p-6 text-center">
      <div className="w-12 h-12 rounded-full bg-[var(--claude-border)]/50 flex items-center justify-center mb-3">
        <MessageSquare className="w-6 h-6 text-[var(--claude-foreground-muted)]" />
      </div>
      <p className="text-sm text-[var(--claude-foreground-muted)]">No conversations yet</p>
      <p className="text-xs text-[var(--claude-foreground-muted)] mt-1">
        Start a new chat to begin
      </p>
    </div>
  );
}

/**
 * Error state when sessions fail to load.
 */
function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-6 text-center">
      <div className="w-12 h-12 rounded-full bg-[var(--claude-error)]/10 flex items-center justify-center mb-3">
        <AlertCircle className="w-6 h-6 text-[var(--claude-error)]" />
      </div>
      <p className="text-sm text-[var(--claude-error)]">Failed to load sessions</p>
      <p className="text-xs text-[var(--claude-foreground-muted)] mt-1 mb-3">{error}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="w-3 h-3 mr-1" />
        Retry
      </Button>
    </div>
  );
}

/**
 * Session group header.
 */
function SessionGroupHeader({ title, count }: { title: string; count: number }) {
  return (
    <div className="flex items-center justify-between px-3 py-2">
      <span className="text-xs font-medium uppercase tracking-wider text-[var(--claude-foreground-muted)]">
        {title}
      </span>
      <span className="text-xs text-[var(--claude-foreground-muted)]">{count}</span>
    </div>
  );
}

export function SessionSidebar({
  currentSessionId,
  onSessionSelect,
  onNewSession,
  className,
  isCollapsed = false,
  onToggleCollapse,
}: SessionSidebarProps) {
  const {
    activeSessionsData,
    historySessionsData,
    isLoading,
    error,
    refresh,
    deleteSession,
    activeSessions,
  } = useSessions({
    autoRefresh: true,
    refreshInterval: 30000,
  });

  const hasActiveSessions = activeSessionsData.length > 0;
  const hasHistorySessions = historySessionsData.length > 0;
  const hasSessions = hasActiveSessions || hasHistorySessions;

  // Collapsed view - just show icons
  if (isCollapsed) {
    return (
      <div
        className={cn(
          'flex flex-col items-center py-4 border-r border-[var(--claude-border)]',
          'bg-[var(--claude-background)]',
          'w-16',
          className
        )}
      >
        {/* Expand button */}
        {onToggleCollapse && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            className="mb-4"
            aria-label="Expand sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        )}

        {/* New session button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onNewSession}
          className="mb-2"
          aria-label="New chat"
        >
          <MessageSquare className="w-4 h-4" />
        </Button>

        {/* Refresh button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={refresh}
          disabled={isLoading}
          className={cn(isLoading && 'animate-spin')}
          aria-label="Refresh sessions"
        >
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex flex-col h-full border-r border-[var(--claude-border)]',
        'bg-[var(--claude-background)]',
        'w-72',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[var(--claude-border)]">
        <h2 className="text-sm font-semibold text-[var(--claude-foreground)]">Chats</h2>
        <div className="flex items-center gap-1">
          {/* Refresh button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={refresh}
            disabled={isLoading}
            className={cn('h-8 w-8', isLoading && '[&>svg]:animate-spin')}
            aria-label="Refresh sessions"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>

          {/* Collapse button */}
          {onToggleCollapse && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="h-8 w-8"
              aria-label="Collapse sidebar"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* New session button */}
      <div className="p-3 border-b border-[var(--claude-border)]">
        <NewSessionButton onClick={onNewSession} />
      </div>

      {/* Session list */}
      <ScrollArea className="flex-1">
        {isLoading && !hasSessions ? (
          <SessionListSkeleton />
        ) : error && !hasSessions ? (
          <ErrorState error={error} onRetry={refresh} />
        ) : !hasSessions ? (
          <EmptyState />
        ) : (
          <div className="py-2">
            {/* Active sessions */}
            {hasActiveSessions && (
              <div className="mb-4">
                <SessionGroupHeader title="Active" count={activeSessionsData.length} />
                <div className="px-2 space-y-1">
                  {activeSessionsData.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={true}
                      isSelected={session.id === currentSessionId}
                      onSelect={() => onSessionSelect(session.id)}
                      onDelete={() => deleteSession(session.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* History sessions */}
            {hasHistorySessions && (
              <div>
                <SessionGroupHeader title="History" count={historySessionsData.length} />
                <div className="px-2 space-y-1">
                  {historySessionsData.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={activeSessions.includes(session.id)}
                      isSelected={session.id === currentSessionId}
                      onSelect={() => onSessionSelect(session.id)}
                      onDelete={() => deleteSession(session.id)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
