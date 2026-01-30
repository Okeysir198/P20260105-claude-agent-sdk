'use client';
import { relativeTime, cn } from '@/lib/utils';
import { useChatStore } from '@/lib/store/chat-store';
import { useDeleteSession, useResumeSession, useUpdateSession } from '@/hooks/use-sessions';
import { useUIStore } from '@/lib/store/ui-store';
import { MessageSquare, Trash2, Pencil, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import type { SessionInfo } from '@/types';
import { apiClient } from '@/lib/api-client';
import { convertHistoryToChatMessages } from '@/lib/history-utils';

interface SessionItemProps {
  session: SessionInfo & {
    snippet?: string;
    matchCount?: number;
  };
  isActive?: boolean;
  selectMode?: boolean;
  isSelected?: boolean;
  onToggleSelect?: () => void;
}

export function SessionItem({
  session,
  isActive,
  selectMode = false,
  isSelected = false,
  onToggleSelect
}: SessionItemProps) {
  const router = useRouter();
  const currentSessionId = useChatStore((s) => s.sessionId);
  const agentId = useChatStore((s) => s.agentId);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const setAgentId = useChatStore((s) => s.setAgentId);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const setMessages = useChatStore((s) => s.setMessages);
  const deleteSession = useDeleteSession();
  const resumeSession = useResumeSession();
  const updateSession = useUpdateSession();
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const isMobile = useUIStore((s) => s.isMobile);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const displayName = session.name || session.first_message || 'New conversation';

  const handleClick = async () => {
    if (isLoading || isDeleting || selectMode || isEditing) return;

    setIsLoading(true);

    try {
      // Navigate to session URL first
      router.push(`/s/${session.session_id}`);

      // Fetch and display history first
      const historyData = await apiClient.getSessionHistory(session.session_id);
      const chatMessages = convertHistoryToChatMessages(historyData.messages);
      clearMessages();
      setMessages(chatMessages);

      // Set the original session ID immediately so messages display
      // Use the ORIGINAL session ID, not the one from resume API
      // This ensures history can be loaded on page refresh
      setSessionId(session.session_id);

      // Set agent ID if available
      if (session.agent_id) {
        setAgentId(session.agent_id);
      }

      // Resume session in background - we don't need the new session ID
      // The WebSocket will use the original session ID for the conversation
      try {
        await resumeSession.mutateAsync({ id: session.session_id });
      } catch (resumeError) {
        // Log but don't fail - session is already loaded
        console.warn('Resume session API failed (non-blocking):', resumeError);
      }

      if (isMobile) {
        setSidebarOpen(false);
      }
    } catch (error) {
      console.error('Failed to load session:', error);
      // Don't clear messages on error - just set the session ID
      // so the user can at least see the session is selected
      setSessionId(session.session_id);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isDeleting || isLoading) return;

    if (confirm('Are you sure you want to delete this conversation?')) {
      setIsDeleting(true);
      try {
        await deleteSession.mutateAsync(session.session_id);

        if (currentSessionId === session.session_id) {
          // Clear state - the useChat effect will handle disconnecting
          // when agentId becomes null, and reconnecting when a new agent is selected
          setSessionId(null);
          setAgentId(null);
          clearMessages();
        }
      } catch (error) {
        console.error('Failed to delete session:', error);
        alert(`Failed to delete session: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  const handleStartEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditName(session.name || '');
    setIsEditing(true);
  };

  const handleCancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditing(false);
    setEditName('');
  };

  const handleSaveEdit = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const newName = editName.trim() || null; // Empty string becomes null

    try {
      await updateSession.mutateAsync({ id: session.session_id, name: newName });
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update session name:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isEditing) {
      e.stopPropagation();
      if (e.key === 'Enter') {
        handleSaveEdit(e as any);
      } else if (e.key === 'Escape') {
        handleCancelEdit(e as any);
      }
      return;
    }

    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (selectMode && onToggleSelect) {
        onToggleSelect();
      } else {
        handleClick();
      }
    }
  };

  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onToggleSelect) {
      onToggleSelect();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={selectMode ? onToggleSelect : handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'group flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left transition-all overflow-hidden',
        'hover:bg-muted/60',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        // Active state: stronger background, left border, shadow
        isActive && !selectMode && 'bg-muted border-l-4 border-foreground shadow-sm',
        isSelected && selectMode && 'bg-primary/10',
        (isDeleting || isLoading) && 'opacity-50'
      )}
    >
      {selectMode ? (
        <div className="flex items-center shrink-0" onClick={handleCheckboxClick}>
          <Checkbox checked={isSelected} className="h-3.5 w-3.5" />
        </div>
      ) : (
        <MessageSquare className={cn(
          "h-3.5 w-3.5 shrink-0",
          isActive ? "text-foreground" : "text-muted-foreground"
        )} />
      )}

      <div className="min-w-0 flex-1">
        {isEditing ? (
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <Input
              ref={inputRef}
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder="Session name"
              className="h-6 text-xs"
              onKeyDown={handleKeyDown}
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0"
              onClick={handleSaveEdit}
              disabled={updateSession.isPending}
            >
              <Check className="h-3 w-3 text-status-success-fg" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0"
              onClick={handleCancelEdit}
            >
              <X className="h-3 w-3 text-status-error-fg" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2 w-full">
            <div className="flex flex-col" style={{ flex: '1 1 0', minWidth: 0 }}>
              <p
                className={cn(
                  "text-sm leading-tight truncate",
                  isActive && "font-semibold text-foreground"
                )}
                title={displayName}
              >
                {displayName}
              </p>
              {session.snippet && (
                <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">
                  {session.matchCount && `${session.matchCount} match${session.matchCount > 1 ? 'es' : ''}: `}
                  {session.snippet}
                </p>
              )}
            </div>
            {/* Timestamp and buttons container - fixed width to prevent jumping */}
            <div className="relative shrink-0 flex items-center justify-end" style={{ minWidth: '48px' }}>
              {/* Timestamp - visible by default, fades on hover */}
              <span className={cn(
                "text-[10px] transition-opacity",
                !selectMode && !isEditing && !(isLoading || isDeleting) && "group-hover:opacity-0",
                isActive ? "text-foreground font-medium" : "text-muted-foreground"
              )}>
                {relativeTime(session.created_at)}
              </span>
              {/* Action buttons - positioned over timestamp, shown on hover */}
              {!selectMode && !isEditing && !(isLoading || isDeleting) && (
                <div className="absolute right-0 flex opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground hover:text-foreground"
                    onClick={handleStartEdit}
                    title="Rename conversation"
                  >
                    <Pencil className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    onClick={handleDelete}
                    title="Delete conversation"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
        {/* Loading indicator */}
        {!selectMode && !isEditing && (isLoading || isDeleting) && (
          <div className="absolute right-0 top-1/2 -translate-y-1/2 h-6 w-6 flex items-center justify-center">
            <div className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        )}
      </div>
    </div>
  );
}
