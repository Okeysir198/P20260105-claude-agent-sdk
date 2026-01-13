'use client';

import { useEffect, useRef } from 'react';
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
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-14 h-14 rounded-2xl bg-surface-tertiary flex items-center justify-center mb-4">
        <MessageSquare className="w-7 h-7 text-text-tertiary" />
      </div>
      <p className="text-sm font-medium text-text-secondary mb-1">No conversations</p>
      <p className="text-xs text-text-tertiary leading-relaxed">
        Click &quot;New Chat&quot; above to start a conversation
      </p>
    </div>
  );
}

/**
 * Error state when sessions fail to load.
 */
function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-14 h-14 rounded-2xl bg-error-50 dark:bg-error-900/20 flex items-center justify-center mb-4">
        <AlertCircle className="w-7 h-7 text-error-500" />
      </div>
      <p className="text-sm font-medium text-text-primary mb-1">Unable to load</p>
      <p className="text-xs text-text-tertiary mb-4 max-w-[200px]">{error}</p>
      <Button
        variant="outline"
        size="sm"
        onClick={onRetry}
        className="rounded-lg"
      >
        <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
        Try again
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
      <span className="text-xs font-medium text-text-tertiary uppercase tracking-wider">
        {title}
      </span>
      <span className="text-xs text-text-tertiary bg-surface-tertiary px-1.5 py-0.5 rounded">
        {count}
      </span>
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
    autoRefresh: false,  // Only refresh on events, not polling
  });

  // Track previous session ID to detect new sessions
  const prevSessionIdRef = useRef<string | null | undefined>(undefined);

  // Refresh when a new session is created (currentSessionId changes to a new value)
  useEffect(() => {
    if (
      currentSessionId &&
      currentSessionId !== prevSessionIdRef.current &&
      !activeSessions.includes(currentSessionId) &&
      !historySessionsData.some((s) => s.id === currentSessionId)
    ) {
      // New session created - refresh the list
      console.log('[SessionSidebar] New session detected, refreshing list:', currentSessionId);
      refresh();
    }
    prevSessionIdRef.current = currentSessionId;
  }, [currentSessionId, activeSessions, historySessionsData, refresh]);

  const hasActiveSessions = activeSessionsData.length > 0;
  const hasHistorySessions = historySessionsData.length > 0;
  const hasSessions = hasActiveSessions || hasHistorySessions;

  // Collapsed view - just show icons
  if (isCollapsed) {
    return (
      <div
        className={cn(
          'flex flex-col items-center py-4',
          'border-r border-border-primary',
          'bg-surface-secondary',
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
            className="mb-4 text-text-secondary hover:text-text-primary"
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
          className="mb-2 text-text-secondary hover:text-claude-orange-600"
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
          className={cn('text-text-secondary hover:text-text-primary', isLoading && 'animate-spin')}
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
        'flex flex-col h-full',
        'border-r border-border-primary',
        'bg-surface-secondary',
        'w-72',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-primary">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-claude-orange-100 dark:bg-claude-orange-900/30 flex items-center justify-center">
            <MessageSquare className="w-4 h-4 text-claude-orange-600 dark:text-claude-orange-400" />
          </div>
          <h2 className="text-sm font-semibold text-text-primary">Chats</h2>
        </div>
        <div className="flex items-center gap-1">
          {/* Refresh button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={refresh}
            disabled={isLoading}
            className={cn('h-8 w-8 text-text-tertiary hover:text-text-primary', isLoading && '[&>svg]:animate-spin')}
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
              className="h-8 w-8 text-text-tertiary hover:text-text-primary"
              aria-label="Collapse sidebar"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* New session button */}
      <div className="p-3">
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
          <div className="py-1">
            {/* Active sessions */}
            {hasActiveSessions && (
              <div className="mb-3">
                <SessionGroupHeader title="Active" count={activeSessionsData.length} />
                <div className="px-2 space-y-0.5">
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
                <div className="px-2 space-y-0.5">
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
