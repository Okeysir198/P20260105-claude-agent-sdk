'use client';

import { useRef, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { Message } from '@/types/messages';
import { MessageItem } from './message-item';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { messageListVariants } from '@/lib/animations';
import { AlertCircle } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  error?: string | null;
  className?: string;
}

export function MessageList({ messages, isStreaming: _isStreaming, error, className }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Filter out empty assistant messages (except streaming ones)
  const filteredMessages = messages.filter((message) => {
    if (message.role === 'assistant') {
      return message.content.trim() !== '' || message.isStreaming;
    }
    return true;
  });

  return (
    <ScrollArea className={cn('flex-1', className)}>
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          className="flex flex-col gap-2 py-6"
          variants={messageListVariants}
          initial="initial"
          animate="animate"
        >
          <AnimatePresence mode="popLayout">
            {filteredMessages.map((message, index) => (
              <MessageItem
                key={message.id}
                message={message}
                isLast={index === filteredMessages.length - 1}
              />
            ))}
          </AnimatePresence>

          {/* Error display */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-3 p-4 rounded-xl bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800"
            >
              <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0" />
              <p className="text-sm text-error-700 dark:text-error-300">{error}</p>
            </motion.div>
          )}
        </motion.div>
        <div ref={endRef} className="h-4" />
      </div>
    </ScrollArea>
  );
}
