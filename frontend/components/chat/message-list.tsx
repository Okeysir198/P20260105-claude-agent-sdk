'use client';
import { useEffect, useRef } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { UserMessage } from './user-message';
import { AssistantMessage } from './assistant-message';
import { ToolUseMessage } from './tool-use-message';
import { ToolResultMessage } from './tool-result-message';
import { TypingIndicator } from './typing-indicator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { WelcomeScreen } from './welcome-screen';

export function MessageList() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Use instant scroll during streaming to prevent jumping
    bottomRef.current?.scrollIntoView({ behavior: isStreaming ? 'instant' : 'smooth' });
  }, [messages, isStreaming]);

  if (messages.length === 0) {
    return <WelcomeScreen />;
  }

  return (
    <ScrollArea className="flex-1">
      <div ref={scrollRef} className="space-y-0 px-4 pb-4 pt-6">
        {messages.map((message) => {
          switch (message.role) {
            case 'user':
              return <UserMessage key={message.id} message={message} />;
            case 'assistant':
              return <AssistantMessage key={message.id} message={message} />;
            case 'tool_use':
              return <ToolUseMessage key={message.id} message={message} />;
            case 'tool_result':
              return <ToolResultMessage key={message.id} message={message} />;
            default:
              return null;
          }
        })}
        {isStreaming && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
