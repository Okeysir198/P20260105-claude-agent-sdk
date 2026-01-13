'use client';

import { useRef, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { Message } from '@/types/messages';
import { MessageItem } from './message-item';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { messageListVariants } from '@/lib/animations';

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  error?: string | null;
  className?: string;
}

export function MessageList({ messages, isStreaming, error, className }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <ScrollArea className={cn('flex-1 px-4', className)}>
      <motion.div
        className="flex flex-col gap-4 py-4"
        variants={messageListVariants}
        initial="initial"
        animate="animate"
      >
        <AnimatePresence mode="popLayout">
          {messages.map((message, index) => (
            <MessageItem
              key={message.id}
              message={message}
              isLast={index === messages.length - 1}
            />
          ))}
        </AnimatePresence>
      </motion.div>
      <div ref={endRef} />
    </ScrollArea>
  );
}
