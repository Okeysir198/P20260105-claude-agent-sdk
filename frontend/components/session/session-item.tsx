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
import type { SessionInfo } from '@/types';
import { apiClient } from '@/lib/api-client';
import { convertHistoryToChatMessages } from '@/lib/history-utils';

interface SessionItemProps {
  session: SessionInfo;
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
      const historyData = await apiClient.getSessionHistory(session.session_id);
      const chatMessages = convertHistoryToChatMessages(historyData.messages);
      clearMessages();
      setMessages(chatMessages);

      const result = await resumeSession.mutateAsync({ id: session.session_id });

      if (result.session_id) {
        setSessionId(result.session_id);
      }

      if (isMobile) {
        setSidebarOpen(false);
      }
    } catch (error) {
      console.error('Failed to resume session:', error);
      clearMessages();
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
        'group flex w-full cursor-pointer items-start gap-2 rounded-lg p-2 text-left transition-colors',
        'hover:bg-muted',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isActive && !selectMode && 'bg-muted',
        isSelected && selectMode && 'bg-primary/10',
        (isDeleting || isLoading) && 'opacity-50'
      )}
    >
      {selectMode ? (
        <div className="flex items-center h-5 mt-0.5" onClick={handleCheckboxClick}>
          <Checkbox checked={isSelected} />
        </div>
      ) : (
        <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground mt-0.5" />
      )}

      <div className="min-w-0 flex-1">
        {isEditing ? (
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <Input
              ref={inputRef}
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder="Session name"
              className="h-7 text-sm"
              onKeyDown={handleKeyDown}
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0"
              onClick={handleSaveEdit}
              disabled={updateSession.isPending}
            >
              <Check className="h-3.5 w-3.5 text-green-600" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0"
              onClick={handleCancelEdit}
            >
              <X className="h-3.5 w-3.5 text-red-600" />
            </Button>
          </div>
        ) : (
          <>
            <p
              className="text-sm font-medium leading-snug line-clamp-2"
              title={displayName}
            >
              {displayName}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {relativeTime(session.created_at)} · {session.turn_count} turns
            </p>
            {session.agent_id && (
              <span className="inline-block text-xs text-muted-foreground/70 bg-muted px-1.5 py-0.5 rounded mt-1">
                {session.agent_id}
              </span>
            )}
          </>
        )}
      </div>

      {!selectMode && !isEditing && (
        (isLoading || isDeleting) ? (
          <div className="h-7 w-7 flex items-center justify-center shrink-0">
            <div className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : (
          <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground"
              onClick={handleStartEdit}
              title="Rename conversation"
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              onClick={handleDelete}
              title="Delete conversation"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )
      )}
    </div>
  );
}
