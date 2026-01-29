'use client';
import { useEffect, useRef, useState, useMemo, useCallback, memo } from 'react';
import { useSessions, useBatchDeleteSessions } from '@/hooks/use-sessions';
import { useChatStore } from '@/lib/store/chat-store';
import { useUIStore } from '@/lib/store/ui-store';
import { SessionItem } from './session-item';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Bot, X, LogOut, User, CheckSquare, Trash2, ChevronDown, Loader2, Search, Check } from 'lucide-react';
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

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchExpanded, setSearchExpanded] = useState(false);

  // Pagination state
  const [displayCount, setDisplayCount] = useState(SESSIONS_PAGE_SIZE);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Reset selection and search when exiting select mode
  useEffect(() => {
    if (!selectMode) {
      setSelectedIds(new Set());
      setSearchQuery('');
      setSearchExpanded(false);
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

  // Filter sessions based on search query
  const { filteredSessions, totalCount, hasMore } = useMemo(() => {
    if (!sessions) return { filteredSessions: [], totalCount: 0, hasMore: false };

    let filtered = sessions;

    // Apply search filter (search both name and first_message)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((session) => {
        const name = session.name || '';
        const firstMessage = session.first_message || '';
        return (
          name.toLowerCase().includes(query) ||
          firstMessage.toLowerCase().includes(query)
        );
      });
    }

    // Apply pagination
    const displayed = filtered.slice(0, displayCount);

    return {
      filteredSessions: displayed,
      totalCount: filtered.length,
      hasMore: filtered.length > displayCount,
    };
  }, [sessions, searchQuery, displayCount]);

  // Handle "Select All" / "Deselect All"
  const handleSelectAll = useCallback(() => {
    if (filteredSessions.length === 0) return;

    const allSelected = filteredSessions.every((session) => selectedIds.has(session.session_id));

    if (allSelected) {
      // Deselect all filtered sessions
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filteredSessions.forEach((session) => next.delete(session.session_id));
        return next;
      });
    } else {
      // Select all filtered sessions
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filteredSessions.forEach((session) => next.add(session.session_id));
        return next;
      });
    }
  }, [filteredSessions, selectedIds]);

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
    <div className="flex h-full w-full flex-col bg-background overflow-hidden">
      <div className="flex h-10 items-center justify-between border-b px-2">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
            <Bot className="h-3.5 w-3.5 text-white" />
          </div>
          <h1 className="text-sm font-semibold whitespace-nowrap">Claude Agent SDK</h1>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSidebarOpen(false)}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Chat History header with select toggle - fixed position */}
      <div className="flex-shrink-0 bg-background border-b px-3 py-2 flex items-center justify-between">
        <h2 className="text-xs font-semibold text-foreground uppercase tracking-wide">History</h2>
        {sessions && sessions.length > 0 && (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setSearchExpanded(!searchExpanded)}
              title="Search conversations"
            >
              <Search className={`h-3.5 w-3.5 ${searchExpanded ? 'text-primary' : ''}`} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setSelectMode(!selectMode)}
              title={selectMode ? "Cancel selection" : "Select sessions"}
            >
              <CheckSquare className={`h-3.5 w-3.5 ${selectMode ? 'text-primary' : ''}`} />
            </Button>
          </div>
        )}
      </div>

      {/* Search bar - expands when search icon is clicked */}
      {searchExpanded && (
        <div className="flex-shrink-0 px-3 py-2 border-b bg-background animate-in slide-in-from-top-1 duration-150">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search name & first message..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-7 pl-8 text-xs pr-8"
                autoFocus
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-0.5 top-1/2 -translate-y-1/2 h-6 w-6"
                  onClick={() => setSearchQuery('')}
                  title="Clear search"
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0"
              onClick={() => {
                setSearchQuery('');
                setSearchExpanded(false);
              }}
              title="Close search"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Batch delete bar (Select All component) - shown in select mode */}
      {selectMode && filteredSessions.length > 0 && (
        <div className="flex items-center justify-between border-b px-2 py-1.5 bg-muted/50">
          <div className="flex items-center gap-2">
            {selectedIds.size > 0 && (
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
            )}
            <span className="text-xs text-muted-foreground">
              {selectedIds.size > 0 ? `${selectedIds.size} of ${filteredSessions.length} selected` : `${filteredSessions.length} conversations`}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs px-2"
            onClick={handleSelectAll}
            title={filteredSessions.every((s) => selectedIds.has(s.session_id)) ? "Deselect all filtered" : "Select all filtered"}
          >
            {filteredSessions.every((s) => selectedIds.has(s.session_id)) ? (
              <>
                <Check className="h-3 w-3 mr-1" />
                Deselect All
              </>
            ) : (
              <>
                <CheckSquare className="h-3 w-3 mr-1" />
                Select All
              </>
            )}
          </Button>
        </div>
      )}

      <ScrollArea className="flex-1" style={{ maxWidth: '100%' }}>
        <div className="space-y-0.5 px-2 pt-2 pb-2" style={{ maxWidth: '100%', width: '100%' }}>
          {isLoading ? (
            <div className="space-y-1">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-8 animate-pulse rounded-md bg-muted" />
              ))}
            </div>
          ) : filteredSessions.length > 0 ? (
            <>
              {/* Session count indicator */}
              {totalCount > SESSIONS_PAGE_SIZE && (
                <div className="px-1 pb-1 text-[10px] text-muted-foreground">
                  {filteredSessions.length}/{totalCount}
                </div>
              )}

              {filteredSessions.map((session) => (
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
                        +{totalCount - filteredSessions.length} more
                      </>
                    )}
                  </Button>
                </div>
              )}
            </>
          ) : (
            <p className="px-1 text-xs text-muted-foreground">
              {searchQuery ? 'No matching conversations' : 'No conversations yet'}
            </p>
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
