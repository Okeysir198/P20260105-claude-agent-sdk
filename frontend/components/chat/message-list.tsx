'use client';

import { useRef, useEffect, useMemo } from 'react';
import { Virtuoso } from 'react-virtuoso';
import type { Message } from '@/types/messages';
import { MessageItem } from './message-item';
import { cn } from '@/lib/utils';
import { AlertCircle } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  error?: string | null;
  className?: string;
}

export function MessageList({ messages, isStreaming, error, className }: MessageListProps) {
  const virtuosoRef = useRef<any>(null);

  // Filter out empty assistant messages (except streaming ones)
  const filteredMessages = useMemo(() => {
    return messages.filter((message) => {
      if (message.role === 'assistant') {
        return message.content.trim() !== '' || message.isStreaming;
      }
      return true;
    });
  }, [messages]);

  // Auto-scroll to bottom on new messages or streaming
  useEffect(() => {
    if (isStreaming || filteredMessages.length > 0) {
      virtuosoRef.current?.scrollToIndex({
        index: filteredMessages.length - 1,
        behavior: 'smooth',
      });
    }
  }, [filteredMessages.length, isStreaming]);

  return (
    <div className={cn('flex-1 flex flex-col', className)}>
      <Virtuoso
        ref={virtuosoRef}
        style={{ flex: 1 }}
        className="scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600 scrollbar-track-transparent"
        data={filteredMessages}
        itemContent={(index, message) => (
          <div className="max-w-4xl mx-auto px-6 py-1">
            <MessageItem
              key={message.id}
              message={message}
              isLast={index === filteredMessages.length - 1}
            />
          </div>
        )}
        components={{
          Header: error ? () => (
            <div className="max-w-4xl mx-auto px-6 py-4">
              <div
                className="flex items-center gap-3 p-4 rounded-xl bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800"
                role="alert"
                aria-live="assertive"
              >
                <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0" aria-hidden="true" />
                <p className="text-sm text-error-700 dark:text-error-300">{error}</p>
              </div>
            </div>
          ) : undefined,
          Footer: () => <div className="h-4" aria-hidden="true" />,
        }}
        role="log"
        aria-live="polite"
        aria-atomic="false"
        aria-label="Chat messages"
        defaultItemHeight={100}
        increaseViewportBy={{ top: 200, bottom: 400 }}
        overscan={200}
      />
    </div>
  );
}
