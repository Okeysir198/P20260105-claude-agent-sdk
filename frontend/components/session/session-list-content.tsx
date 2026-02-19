'use client';

import { memo, useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useSessions, useBatchDeleteSessions } from '@/hooks/use-sessions';
import { useSessionSearch } from '@/hooks/use-session-search';
import { useChatStore } from '@/lib/store/chat-store';
import { useKanbanStore } from '@/lib/store/kanban-store';
import { SessionItem } from './session-item';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { CheckSquare, Trash2, ChevronDown, Loader2, Search, Check } from 'lucide-react';
import type { SessionInfo } from '@/types/api';

// Memoize SessionItem to prevent unnecessary re-renders
const MemoizedSessionItem = memo(SessionItem);

// Number of sessions to load initially and per "Load more" click
const SESSIONS_PAGE_SIZE = 20;

interface SessionListContentProps {
  sessions: SessionInfo[];
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
  isLoading?: boolean;
}

export function SessionListContent({
  sessions,
  currentSessionId,
  onSessionSelect,
  onNewSession,
  isLoading,
}: SessionListContentProps) {
  const sessionId = useChatStore((s) => s.sessionId);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const setAgentId = useChatStore((s) => s.setAgentId);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const batchDelete = useBatchDeleteSessions();

  // Multi-select state
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchExpanded, setSearchExpanded] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Pagination state
  const [displayCount, setDisplayCount] = useState(SESSIONS_PAGE_SIZE);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Backend search hook (active when search is expanded)
  const { data: searchResults, isLoading: isSearching, error: searchError } = useSessionSearch(
    searchQuery,
    {
      enabled: searchExpanded
    }
  );

  // Reset selection and search when exiting select mode
  useEffect(() => {
    if (!selectMode) {
      setSelectedIds(new Set());
      setSearchQuery('');
      setSearchExpanded(false);
    }
  }, [selectMode]);

  // Reset display count when sessions list changes (e.g., after deletion)
  useEffect(() => {
    if (sessions && sessions.length < displayCount) {
      setDisplayCount(Math.max(SESSIONS_PAGE_SIZE, sessions.length));
    }
  }, [sessions, displayCount]);

  // Filter sessions based on search query
  const { filteredSessions, totalCount, hasMore } = useMemo(() => {
    if (!sessions) return { filteredSessions: [], totalCount: 0, hasMore: false };

    // Use backend search when there's a query
    if (searchQuery.trim()) {
      // If we have search results, use them
      if (searchResults && searchResults.results) {
        const results = searchResults.results.map((r: any) => ({
          session_id: r.session_id,
          name: r.name,
          first_message: r.first_message,
          created_at: r.created_at,
          turn_count: r.turn_count,
          agent_id: r.agent_id,
          user_id: null,
          snippet: r.snippet,
          matchCount: r.match_count
        }));

        return {
          filteredSessions: results.slice(0, displayCount),
          totalCount: results.length,
          hasMore: results.length > displayCount
        };
      }
      // If we're searching but don't have results yet, show empty
      return { filteredSessions: [], totalCount: 0, hasMore: false };
    }

    // No query - show all sessions with pagination
    const displayed = sessions.slice(0, displayCount);

    return {
      filteredSessions: displayed,
      totalCount: sessions.length,
      hasMore: sessions.length > displayCount,
    };
  }, [sessions, searchQuery, searchResults, displayCount]);

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

  // Clear search query and optionally close search
  const handleClearSearch = useCallback((closeSearch = false) => {
    setSearchQuery('');
    if (closeSearch) {
      setSearchExpanded(false);
    }
    // Refocus input if not closing
    if (!closeSearch && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, []);

  // Handle keyboard events for search input
  const handleSearchKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      if (searchQuery) {
        // Clear search if there's text
        handleClearSearch(false);
      } else {
        // Close search if already empty
        handleClearSearch(true);
      }
    }
  }, [searchQuery, handleClearSearch]);

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
          useKanbanStore.getState().reset();
        }

        setSelectMode(false);
      } catch (error) {
        console.error('Batch delete failed:', error);
      }
    }
  };

  return (
    <>
      {/* Search bar - expands when search icon is clicked */}
      {searchExpanded && (
        <div className="flex-shrink-0 px-3 py-2 border-b bg-background animate-in slide-in-from-top-1 duration-150">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
              <Input
                ref={searchInputRef}
                type="text"
                placeholder="Search all messages..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                className="h-7 pl-8 text-xs pr-8"
                autoFocus
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-0.5 top-1/2 -translate-y-1/2 h-6 w-6 hover:bg-muted opacity-70 hover:opacity-100 transition-opacity"
                  onClick={() => handleClearSearch(false)}
                  title="Clear search (Escape)"
                  type="button"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>
          {isSearching && (
            <div className="flex items-center gap-2 px-1 py-1.5 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              Searching...
            </div>
          )}
          {searchError && (
            <div className="flex items-center gap-2 px-1 py-1.5 text-xs text-destructive">
              <span>Search failed. Please try again.</span>
            </div>
          )}
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

      {/* Session list header with select toggle */}
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

      <ScrollArea className="flex-1 h-full" style={{ maxWidth: '100%' }}>
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
              {searchError
                ? 'Search failed. Please try again.'
                : searchQuery
                  ? 'No matching conversations'
                  : 'No conversations yet'}
            </p>
          )}
        </div>
      </ScrollArea>
    </>
  );
}
