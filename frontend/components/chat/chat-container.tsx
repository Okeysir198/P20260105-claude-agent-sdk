'use client';

import { useEffect, useRef } from 'react';
import { useClaudeChat } from '@/hooks/use-claude-chat';
import { ChatHeader } from './chat-header';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { WelcomeScreen } from './welcome-screen';
import { AmbientGlow } from '@/components/animations/ambient-glow';
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
  /** Mobile menu props */
  mobileMenuOpen?: boolean;
  onMobileMenuToggle?: () => void;
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
  mobileMenuOpen = false,
  onMobileMenuToggle,
}: ChatContainerProps) {
  const chat = useClaudeChat({
    agentId: selectedAgentId || undefined,
    onSessionCreated: onSessionChange,
    onDone: (_turnCount, _cost) => {
      // Optional: Track usage metrics here
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
    <div className={cn('flex flex-col h-full relative overflow-hidden', 'bg-surface-primary', className)}>
      {/* Ambient AI glow indicator */}
      <AmbientGlow
        isActive={chat.isStreaming}
        size="lg"
        variant="orange"
        position="top"
        useGradient={false}
      />

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
          mobileMenuOpen={mobileMenuOpen}
          onMobileMenuToggle={onMobileMenuToggle}
        />
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-h-0 relative z-10">
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

      {/* Input area with floating design - responsive padding */}
      <div className="px-3 md:px-6 pb-3 md:pb-6 pt-2 safe-bottom relative z-10">
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
