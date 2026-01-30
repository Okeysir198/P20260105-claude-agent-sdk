'use client';

import { useState, useRef, useEffect } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useSessions, useUpdateSession } from '@/hooks/use-sessions';
import { cn } from '@/lib/utils';

export function SessionTitle() {
  const sessionId = useChatStore((s) => s.sessionId);
  const { data: sessions } = useSessions();
  const updateSession = useUpdateSession();
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const currentSession = sessions?.find((s) => s.session_id === sessionId);
  const displayTitle =
    currentSession?.name ||
    currentSession?.first_message?.slice(0, 50) ||
    'Untitled Conversation';

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleStartEdit = () => {
    if (!sessionId) return;
    setEditValue(currentSession?.name || '');
    setIsEditing(true);
  };

  const handleSave = () => {
    if (!sessionId) return;
    const trimmedValue = editValue.trim();
    // Only update if the value changed
    if (trimmedValue !== (currentSession?.name || '')) {
      updateSession.mutate({
        id: sessionId,
        name: trimmedValue || null, // null to clear custom name
      });
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
    }
  };

  if (!sessionId) {
    return (
      <span className="text-sm font-medium text-muted-foreground truncate">
        No active conversation
      </span>
    );
  }

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        placeholder="Untitled Conversation"
        className={cn(
          'text-sm font-medium bg-transparent border-b border-primary',
          'outline-none min-w-[150px] max-w-[300px]',
          'placeholder:text-muted-foreground'
        )}
      />
    );
  }

  return (
    <button
      onClick={handleStartEdit}
      className={cn(
        'text-sm font-medium truncate max-w-[200px] sm:max-w-[300px]',
        'hover:text-foreground/80 transition-colors text-left',
        currentSession?.name ? 'text-foreground' : 'text-muted-foreground'
      )}
      title={`${displayTitle} (click to edit)`}
    >
      {displayTitle}
    </button>
  );
}
