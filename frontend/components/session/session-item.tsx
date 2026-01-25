'use client';
import { relativeTime, cn } from '@/lib/utils';
import { useChatStore } from '@/lib/store/chat-store';
import { useDeleteSession, useResumeSession } from '@/hooks/use-sessions';
import { useUIStore } from '@/lib/store/ui-store';
import { MessageSquare, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import type { SessionInfo } from '@/types';
import { apiClient } from '@/lib/api-client';
import { convertHistoryToChatMessages } from '@/lib/history-utils';

interface SessionItemProps {
  session: SessionInfo;
  isActive?: boolean;
}

export function SessionItem({ session, isActive }: SessionItemProps) {
  const currentSessionId = useChatStore((s) => s.sessionId);
  const agentId = useChatStore((s) => s.agentId);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const setAgentId = useChatStore((s) => s.setAgentId);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const setMessages = useChatStore((s) => s.setMessages);
  const deleteSession = useDeleteSession();
  const resumeSession = useResumeSession();
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const isMobile = useUIStore((s) => s.isMobile);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async () => {
    if (isLoading || isDeleting) return;

    setIsLoading(true);

    try {
      // Fetch session history first before clearing
      const historyData = await apiClient.getSessionHistory(session.session_id);

      // Convert and load history messages
      const chatMessages = convertHistoryToChatMessages(historyData.messages);
      clearMessages();
      setMessages(chatMessages);

      // Call resume API to get new session ID
      const result = await resumeSession.mutateAsync({ id: session.session_id });

      // Set the new session ID after loading history
      if (result.session_id) {
        setSessionId(result.session_id);
      }

      // Close sidebar on mobile after session selection
      if (isMobile) {
        setSidebarOpen(false);
      }
    } catch (error) {
      console.error('Failed to resume session:', error);
      clearMessages();
      // If resume fails, still try to connect with the session_id
      // The WebSocket will handle the "not found" error gracefully
      setSessionId(session.session_id);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    console.log('Delete button clicked for session:', session.session_id);

    if (isDeleting || isLoading) {
      console.log('Delete blocked: already deleting or loading');
      return;
    }

    if (confirm('Are you sure you want to delete this conversation?')) {
      console.log('Proceeding with delete for session:', session.session_id);
      setIsDeleting(true);
      try {
        await deleteSession.mutateAsync(session.session_id);
        console.log('Delete successful for session:', session.session_id);

        // If we deleted the current active session, reset state
        if (currentSessionId === session.session_id) {
          console.log('Deleted active session, resetting state');
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
    } else {
      console.log('Delete cancelled by user');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'group flex w-full cursor-pointer items-start gap-2 rounded-lg p-2 text-left transition-colors',
        'hover:bg-muted',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isActive && 'bg-muted',
        (isDeleting || isLoading) && 'opacity-50'
      )}
    >
      <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground mt-0.5" />
      <div className="min-w-0 flex-1">
        <p
          className="text-sm font-medium leading-snug line-clamp-2"
          title={session.first_message || 'New conversation'}
        >
          {session.first_message || 'New conversation'}
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {relativeTime(session.created_at)} · {session.turn_count} turns
        </p>
      </div>
      {(isLoading || isDeleting) ? (
        <div className="h-7 w-7 flex items-center justify-center shrink-0">
          <div className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-opacity"
          onClick={handleDelete}
          title="Delete conversation"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}
