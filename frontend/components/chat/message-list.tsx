'use client';
import { useEffect, useRef, useState, useMemo, useCallback, memo } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useQuestionStore } from '@/lib/store/question-store';
import { UserMessage } from './user-message';
import { AssistantMessage } from './assistant-message';
import { ToolUseMessage } from './tool-use-message';
import { TypingIndicator } from './typing-indicator';
// Using native scroll instead of Radix ScrollArea due to positioning bug
import { Skeleton } from '@/components/ui/skeleton';
import { WelcomeScreen } from './welcome-screen';
import type { ChatMessage } from '@/types';

// Memoized message components to prevent unnecessary re-renders
const MemoizedUserMessage = memo(UserMessage);
const MemoizedAssistantMessage = memo(AssistantMessage);
const MemoizedToolUseMessage = memo(ToolUseMessage);

/**
 * Skeleton loading state for messages
 */
function MessageSkeleton() {
  return (
    <div className="px-2 sm:px-4 pb-4 pt-4 space-y-4 animate-in fade-in duration-300">
      {/* User message skeleton */}
      <div className="flex justify-end">
        <div className="max-w-[80%] space-y-2">
          <Skeleton className="h-4 w-48 ml-auto" />
          <Skeleton className="h-12 w-64 rounded-2xl" />
        </div>
      </div>

      {/* Assistant message skeleton */}
      <div className="flex gap-3">
        <Skeleton className="h-8 w-8 rounded-full shrink-0" />
        <div className="space-y-2 flex-1 max-w-[80%]">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-20 w-full rounded-xl" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>

      {/* Tool use skeleton */}
      <div className="flex gap-3">
        <Skeleton className="h-7 w-7 rounded-md shrink-0" />
        <div className="space-y-2 flex-1 max-w-2xl">
          <Skeleton className="h-9 w-full rounded-lg" />
        </div>
      </div>

      {/* Another assistant message skeleton */}
      <div className="flex gap-3">
        <Skeleton className="h-8 w-8 rounded-full shrink-0" />
        <div className="space-y-2 flex-1 max-w-[80%]">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      </div>
    </div>
  );
}

export function MessageList() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const connectionStatus = useChatStore((s) => s.connectionStatus);
  // Subscribe to submittedAnswers to trigger re-render when user answers questions
  const submittedAnswers = useQuestionStore((s) => s.submittedAnswers);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const spacerRef = useRef<HTMLDivElement>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  // Track initial load state - show skeleton briefly while hydrating
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsInitialLoad(false);
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    // Scroll within the container only, not the document
    const container = containerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, isStreaming]);

  // Helper to find the tool_result for a tool_use message
  // Memoized to prevent recalculation on every render
  // NOTE: Must be defined before any early returns to follow Rules of Hooks
  const findToolResult = useCallback((toolUseId: string, messageIndex: number): ChatMessage | undefined => {
    // First try direct ID match using the actual toolUseId from the tool_use message
    const toolUseMessage = messages[messageIndex];
    const actualToolUseId = toolUseMessage?.toolUseId || toolUseId;

    const directMatch = messages.find(m => m.role === 'tool_result' && m.toolUseId === actualToolUseId);
    if (directMatch) {
      return directMatch;
    }

    // Fallback: find the next tool_result after this message
    for (let i = messageIndex + 1; i < messages.length; i++) {
      if (messages[i].role === 'tool_result') {
        return messages[i];
      }
      // Stop if we hit another tool_use (means this one wasn't answered)
      if (messages[i].role === 'tool_use') {
        break;
      }
    }
    return undefined;
  }, [messages]);

  // Find the last tool_use message index
  // NOTE: Must be defined before any early returns to follow Rules of Hooks
  const lastToolUseIndex = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'tool_use') {
        return i;
      }
    }
    return -1;
  }, [messages]);

  // Memoize the rendered message list to prevent unnecessary re-renders
  // NOTE: Must be defined before any early returns to follow Rules of Hooks
  const renderedMessages = useMemo(() => {
    return messages.map((message, index) => {
      switch (message.role) {
        case 'user':
          return <MemoizedUserMessage key={message.id} message={message} />;
        case 'assistant':
          return <MemoizedAssistantMessage key={message.id} message={message} />;
        case 'tool_use': {
          // Find the corresponding tool_result for this tool_use
          const toolResult = findToolResult(message.id, index);
          // Determine if this tool is currently running:
          // - It's the last tool_use message
          // - The stream is still active
          // - No result has arrived yet
          const isToolRunning = isStreaming && index === lastToolUseIndex && !toolResult;

          // For AskUserQuestion, include submitted answers in key to force re-render when user answers
          let componentKey = toolResult ? `${message.id}-${toolResult.id}` : message.id;
          if (message.toolName === 'AskUserQuestion') {
            const hasSubmittedAnswer = submittedAnswers[message.id] ? 'answered' : 'pending';
            componentKey = `${componentKey}-${hasSubmittedAnswer}`;
          }

          return (
            <MemoizedToolUseMessage
              key={componentKey}
              message={message}
              result={toolResult}
              isRunning={isToolRunning}
            />
          );
        }
        case 'tool_result':
          // Skip - tool_result is now displayed within ToolUseMessage
          return null;
        default:
          return null;
      }
    });
  }, [messages, findToolResult, isStreaming, lastToolUseIndex, submittedAnswers]);

  // Show skeleton during initial load when reconnecting to existing session
  if (isInitialLoad && connectionStatus === 'connecting') {
    return (
      <div className="h-full overflow-y-auto">
        <MessageSkeleton />
      </div>
    );
  }

  if (messages.length === 0) {
    return <WelcomeScreen />;
  }

  return (
    <div ref={containerRef} className="h-full overflow-y-auto overflow-x-hidden">
      <div ref={spacerRef} className="h-32 md:h-0 shrink-0" />
      <div ref={scrollRef} className="px-2 sm:px-4 pb-4 pt-4 min-w-0">
        {renderedMessages}
        {isStreaming && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
