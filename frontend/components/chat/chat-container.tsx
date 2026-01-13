'use client';

import { useEffect, useRef } from 'react';
import { useClaudeChat } from '@/hooks/use-claude-chat';
import { ChatHeader } from './chat-header';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { cn } from '@/lib/utils';

interface ChatContainerProps {
  className?: string;
  apiBaseUrl?: string;
  showHeader?: boolean;
  /** Selected session ID to load - when this changes, history is loaded */
  selectedSessionId?: string | null;
  onSessionChange?: (sessionId: string | null) => void;
}

export function ChatContainer({
  className,
  apiBaseUrl,
  showHeader = true,
  selectedSessionId,
  onSessionChange,
}: ChatContainerProps) {
  const chat = useClaudeChat({
    apiBaseUrl,
    onSessionCreated: onSessionChange,
    onError: (error) => {
      console.error('[ChatContainer] Error:', error);
    },
    onDone: (turnCount, cost) => {
      console.log(`[ChatContainer] Turn complete. Turns: ${turnCount}, Cost: $${cost?.toFixed(4) ?? 'N/A'}`);
    },
  });

  // Track the previous session ID to detect changes
  const prevSelectedSessionIdRef = useRef<string | null | undefined>(undefined);

  // Load history when selectedSessionId changes
  useEffect(() => {
    // Skip initial render and avoid re-loading same session
    if (prevSelectedSessionIdRef.current === selectedSessionId) {
      return;
    }
    prevSelectedSessionIdRef.current = selectedSessionId;

    if (selectedSessionId && selectedSessionId !== chat.sessionId) {
      console.log('[ChatContainer] Loading history for session:', selectedSessionId);
      chat.resumeSession(selectedSessionId);
    } else if (selectedSessionId === null && chat.sessionId !== null) {
      // User clicked "New Chat" - clear messages
      chat.clearMessages();
    }
  }, [selectedSessionId, chat.sessionId, chat.resumeSession, chat.clearMessages]);

  const handleNewSession = () => {
    chat.startNewSession();
    onSessionChange?.(null);
  };

  const handleClear = () => {
    chat.clearMessages();
    onSessionChange?.(null);
  };

  return (
    <div className={cn('flex flex-col h-full', 'bg-[var(--claude-background)]', className)}>
      {showHeader && (
        <ChatHeader
          sessionId={chat.sessionId}
          turnCount={chat.turnCount}
          isStreaming={chat.isStreaming}
          onNewSession={handleNewSession}
          onClear={handleClear}
        />
      )}
      <MessageList
        messages={chat.messages}
        isStreaming={chat.isStreaming}
        error={chat.error}
      />
      <ChatInput
        onSend={chat.sendMessage}
        onInterrupt={chat.interrupt}
        isLoading={chat.isLoading}
        isStreaming={chat.isStreaming}
        disabled={chat.isLoading && !chat.isStreaming}
      />
    </div>
  );
}
