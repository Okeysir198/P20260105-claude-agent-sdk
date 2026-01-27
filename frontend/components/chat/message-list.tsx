'use client';
import { useEffect, useRef } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { UserMessage } from './user-message';
import { AssistantMessage } from './assistant-message';
import { ToolUseMessage } from './tool-use-message';
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

  // Helper to find the tool_result for a tool_use message
  // Uses sequential matching since tool_use_id may not match in backend history
  const findToolResult = (toolUseId: string, messageIndex: number) => {
    // First try direct ID match
    const directMatch = messages.find(m => m.role === 'tool_result' && m.toolUseId === toolUseId);
    if (directMatch) return directMatch;

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
  };

  return (
    <ScrollArea className="h-full">
      <div ref={scrollRef} className="px-4 pb-4 pt-4">
        {messages.map((message, index) => {
          switch (message.role) {
            case 'user':
              return <UserMessage key={message.id} message={message} />;
            case 'assistant':
              return <AssistantMessage key={message.id} message={message} />;
            case 'tool_use': {
              // Find the corresponding tool_result for this tool_use
              const toolResult = findToolResult(message.id, index);
              return (
                <ToolUseMessage
                  key={message.id}
                  message={message}
                  result={toolResult}
                />
              );
            }
            case 'tool_result':
              // Skip - tool_result is now displayed within ToolUseMessage
              return null;
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
