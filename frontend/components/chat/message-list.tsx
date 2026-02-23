'use client';
import { useEffect, useRef, useState, useMemo, useCallback, memo } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useQuestionStore } from '@/lib/store/question-store';
import { UserMessage } from './user-message';
import { AssistantMessage } from './assistant-message';
import { ToolUseMessage } from './tool-use-message';
import { TypingIndicator } from './typing-indicator';
import { Skeleton } from '@/components/ui/skeleton';
import { WelcomeScreen } from './welcome-screen';
import type { ChatMessage } from '@/types';

const MemoizedUserMessage = memo(UserMessage);
const MemoizedAssistantMessage = memo(AssistantMessage);
const MemoizedToolUseMessage = memo(ToolUseMessage);

function MessageSkeleton() {
  return (
    <div className="px-2 sm:px-4 pb-4 pt-4 space-y-4 animate-in fade-in duration-300">
      <div className="flex justify-end">
        <div className="max-w-[80%] space-y-2">
          <Skeleton className="h-4 w-48 ml-auto" />
          <Skeleton className="h-12 w-64 rounded-2xl" />
        </div>
      </div>

      <div className="flex gap-3">
        <Skeleton className="h-8 w-8 rounded-full shrink-0" />
        <div className="space-y-2 flex-1 max-w-[80%]">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-20 w-full rounded-xl" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>

      <div className="flex gap-3">
        <Skeleton className="h-7 w-7 rounded-md shrink-0" />
        <div className="space-y-2 flex-1 max-w-2xl">
          <Skeleton className="h-9 w-full rounded-lg" />
        </div>
      </div>

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
  const submittedAnswers = useQuestionStore((s) => s.submittedAnswers);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const spacerRef = useRef<HTMLDivElement>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsInitialLoad(false);
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, isStreaming]);

  const findToolResult = useCallback((toolUseId: string, messageIndex: number): ChatMessage | undefined => {
    const toolUseMessage = messages[messageIndex];
    const actualToolUseId = toolUseMessage?.toolUseId || toolUseId;

    const directMatch = messages.find(m => m.role === 'tool_result' && m.toolUseId === actualToolUseId);
    if (directMatch) {
      return directMatch;
    }

    for (let i = messageIndex + 1; i < messages.length; i++) {
      if (messages[i].role === 'tool_result') {
        return messages[i];
      }
      if (messages[i].role === 'tool_use') {
        break;
      }
    }
    return undefined;
  }, [messages]);

  const lastToolUseIndex = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'tool_use') {
        return i;
      }
    }
    return -1;
  }, [messages]);

  const renderedMessages = useMemo(() => {
    return messages.map((message, index) => {
      switch (message.role) {
        case 'user':
          return <MemoizedUserMessage key={message.id} message={message} />;
        case 'assistant':
          return <MemoizedAssistantMessage key={message.id} message={message} />;
        case 'tool_use': {
          const toolResult = findToolResult(message.id, index);
          const isToolRunning = isStreaming && index === lastToolUseIndex && !toolResult;

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
          return null;
        default:
          return null;
      }
    });
  }, [messages, findToolResult, isStreaming, lastToolUseIndex, submittedAnswers]);

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
      <div ref={spacerRef} className="h-10 md:h-0 shrink-0" />
      <div ref={scrollRef} className="px-2 sm:px-4 pb-4 pt-4 min-w-0">
        {renderedMessages}
        {isStreaming && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
