'use client';
import { useEffect, useRef, useState, useMemo, useCallback, memo } from 'react';
import { useSessions, useBatchDeleteSessions } from '@/hooks/use-sessions';
import { useChatStore } from '@/lib/store/chat-store';
import { useUIStore } from '@/lib/store/ui-store';
import { SessionItem } from './session-item';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Bot, X, LogOut, User, CheckSquare, Trash2, ChevronDown, Loader2 } from 'lucide-react';
import { useAuth } from '@/components/providers/auth-provider';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

// Memoize SessionItem to prevent unnecessary re-renders
const MemoizedSessionItem = memo(SessionItem);

// Number of sessions to load initially and per "Load more" click
const SESSIONS_PAGE_SIZE = 20;

export function SessionSidebar() {
  const { user, logout } = useAuth();
  const { data: sessions, isLoading } = useSessions();
  const sessionId = useChatStore((s) => s.sessionId);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const setAgentId = useChatStore((s) => s.setAgentId);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const hadSessionsRef = useRef(false);

  // Multi-select state
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const batchDelete = useBatchDeleteSessions();

  // Pagination state
  const [displayCount, setDisplayCount] = useState(SESSIONS_PAGE_SIZE);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Reset selection when exiting select mode
  useEffect(() => {
    if (!selectMode) {
      setSelectedIds(new Set());
    }
  }, [selectMode]);

  // Track if we've ever had sessions
  useEffect(() => {
    if (sessions && sessions.length > 0) {
      hadSessionsRef.current = true;
    }
  }, [sessions]);

  // NOTE: We previously had an effect here to clear state when all sessions are deleted.
  // This was removed because it caused race conditions:
  // 1. User deletes session, sessions list becomes empty
  // 2. User immediately sends a new message
  // 3. New session is created via WebSocket, sessionId is set
  // 4. Sessions query refetches, but briefly shows 0 before the new session appears
  // 5. The old effect would detect sessions.length === 0 && sessionId exists
  // 6. And incorrectly clear messages/state
  //
  // The proper cleanup is now handled by:
  // - session-item.tsx handleDelete: clears state when deleting current session
  // - session-sidebar.tsx handleBatchDelete: clears state when bulk deleting current session
  // - No automatic cleanup needed when sessions become empty

  // Reset display count when sessions list changes (e.g., after deletion)
  useEffect(() => {
    if (sessions && sessions.length < displayCount) {
      setDisplayCount(Math.max(SESSIONS_PAGE_SIZE, sessions.length));
    }
  }, [sessions, displayCount]);

  // Memoize displayed sessions for pagination
  const { displayedSessions, totalCount, hasMore } = useMemo(() => {
    if (!sessions) return { displayedSessions: [], totalCount: 0, hasMore: false };
    return {
      displayedSessions: sessions.slice(0, displayCount),
      totalCount: sessions.length,
      hasMore: sessions.length > displayCount,
    };
  }, [sessions, displayCount]);

  // Handle "Load more" button click
  const handleLoadMore = useCallback(() => {
    setIsLoadingMore(true);
    // Simulate a small delay for smoother UX
    setTimeout(() => {
      setDisplayCount((prev) => prev + SESSIONS_PAGE_SIZE);
      setIsLoadingMore(false);
    }, 150);
  }, []);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;

    if (confirm(`Delete ${selectedIds.size} conversation${selectedIds.size > 1 ? 's' : ''}?`)) {
      try {
        await batchDelete.mutateAsync(Array.from(selectedIds));

        // If we deleted the current session, clear state
        if (sessionId && selectedIds.has(sessionId)) {
          setSessionId(null);
          setAgentId(null);
          clearMessages();
        }

        setSelectMode(false);
      } catch (error) {
        console.error('Batch delete failed:', error);
      }
    }
  };

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="flex h-10 items-center justify-between border-b px-2">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
            <Bot className="h-3.5 w-3.5 text-white" />
          </div>
          <h1 className="text-sm font-semibold whitespace-nowrap">Agent Chat</h1>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSidebarOpen(false)}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Batch delete bar */}
      {selectMode && selectedIds.size > 0 && (
        <div className="flex items-center justify-between border-b px-2 py-1.5 bg-muted/50">
          <span className="text-xs text-muted-foreground">
            {selectedIds.size} selected
          </span>
          <Button
            variant="destructive"
            size="sm"
            className="h-6 text-xs px-2"
            onClick={handleBatchDelete}
            disabled={batchDelete.isPending}
          >
            <Trash2 className="h-3 w-3 mr-1" />
            Delete
          </Button>
        </div>
      )}

      <ScrollArea className="flex-1">
        <div className="space-y-0.5 px-2 pt-2 pb-2">
          {/* Chat History header with select toggle */}
          <div className="flex items-center justify-between px-1 pb-1.5">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">History</h2>
            {sessions && sessions.length > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setSelectMode(!selectMode)}
                title={selectMode ? "Cancel selection" : "Select sessions"}
              >
                <CheckSquare className={`h-3.5 w-3.5 ${selectMode ? 'text-primary' : ''}`} />
              </Button>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-1">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-8 animate-pulse rounded-md bg-muted" />
              ))}
            </div>
          ) : displayedSessions.length > 0 ? (
            <>
              {/* Session count indicator */}
              {totalCount > SESSIONS_PAGE_SIZE && (
                <div className="px-1 pb-1 text-[10px] text-muted-foreground">
                  {displayedSessions.length}/{totalCount}
                </div>
              )}

              {displayedSessions.map((session) => (
                <MemoizedSessionItem
                  key={session.session_id}
                  session={session}
                  isActive={session.session_id === sessionId}
                  selectMode={selectMode}
                  isSelected={selectedIds.has(session.session_id)}
                  onToggleSelect={() => toggleSelect(session.session_id)}
                />
              ))}

              {/* Load more button */}
              {hasMore && (
                <div className="pt-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full h-7 text-[10px] text-muted-foreground hover:text-foreground"
                    onClick={handleLoadMore}
                    disabled={isLoadingMore}
                  >
                    {isLoadingMore ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-1.5 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      <>
                        <ChevronDown className="h-3 w-3 mr-1.5" />
                        +{totalCount - displayCount} more
                      </>
                    )}
                  </Button>
                </div>
              )}
            </>
          ) : (
            <p className="px-1 text-xs text-muted-foreground">No conversations yet</p>
          )}
        </div>
      </ScrollArea>

      {/* User profile at bottom */}
      {user && (
        <div className="border-t p-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="w-full justify-start gap-2 h-8 px-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <User className="h-3 w-3" />
                </div>
                <span className="text-sm truncate">{user.full_name || user.username}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48">
              <DropdownMenuLabel className="py-1.5">
                <span className="text-sm">{user.username}</span>
                <p className="text-[10px] font-normal text-muted-foreground">{user.role}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="text-destructive text-sm py-1.5">
                <LogOut className="mr-2 h-3.5 w-3.5" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </div>
  );
}
