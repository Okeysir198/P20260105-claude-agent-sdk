'use client';

import { useEffect, useRef } from 'react';
import { useClaudeChat } from '@/hooks/use-claude-chat';
import { ChatHeader } from './chat-header';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { WelcomeScreen } from './welcome-screen';
import { cn } from '@/lib/utils';
import { Agent } from '@/hooks/use-agents';

interface ChatContainerProps {
  className?: string;
  showHeader?: boolean;
  /** Selected session ID to load - when this changes, history is loaded */
  selectedSessionId?: string | null;
  onSessionChange?: (sessionId: string | null) => void;
  /** Agent selection props */
  agents?: Agent[];
  selectedAgentId?: string | null;
  onAgentChange?: (agentId: string) => void;
  agentsLoading?: boolean;
}

export function ChatContainer({
  className,
  showHeader = false,
  selectedSessionId,
  onSessionChange,
  agents = [],
  selectedAgentId,
  onAgentChange,
  agentsLoading = false,
}: ChatContainerProps) {
  const chat = useClaudeChat({
    agentId: selectedAgentId || undefined,
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

  const hasMessages = chat.messages.length > 0;

  return (
    <div className={cn('flex flex-col h-full', 'bg-surface-primary', className)}>
      {showHeader && (
        <ChatHeader
          sessionId={chat.sessionId}
          turnCount={chat.turnCount}
          isStreaming={chat.isStreaming}
          onNewSession={handleNewSession}
          onClear={handleClear}
          agents={agents}
          selectedAgentId={selectedAgentId}
          onAgentChange={onAgentChange}
          agentsLoading={agentsLoading}
        />
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-h-0">
        {hasMessages ? (
          <MessageList
            messages={chat.messages}
            isStreaming={chat.isStreaming}
            error={chat.error}
          />
        ) : (
          <WelcomeScreen />
        )}
      </div>

      {/* Input area with floating design */}
      <div className="px-6 pb-6 pt-2">
        <div className="max-w-4xl mx-auto">
          <ChatInput
            onSend={chat.sendMessage}
            onInterrupt={chat.interrupt}
            isLoading={chat.isLoading}
            isStreaming={chat.isStreaming}
            disabled={chat.isLoading && !chat.isStreaming}
          />
        </div>
      </div>
    </div>
  );
}
