'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import type { Message } from '@/types/messages';
import { UserMessage } from './user-message';
import { AssistantMessage } from './assistant-message';
import { ToolUseMessage } from './tool-use-message';
import { ToolResultMessage } from './tool-result-message';
import { cn } from '@/lib/utils';
import { messageVariants } from '@/lib/animations';

interface MessageItemProps {
  message: Message;
  isLast?: boolean;
}

export const MessageItem = memo(function MessageItem({ message, isLast }: MessageItemProps) {
  // Route to appropriate message component based on role
  const renderMessage = () => {
    switch (message.role) {
      case 'user':
        return <UserMessage message={message} />;
      case 'assistant':
        return <AssistantMessage message={message} />;
      case 'tool_use':
        return <ToolUseMessage message={message} />;
      case 'tool_result':
        return <ToolResultMessage message={message} />;
      case 'system':
        // System messages can be rendered as a simple notification
        return (
          <div
            className={cn(
              'text-sm px-4 py-2 rounded-md text-center',
              message.level === 'error' && 'bg-[var(--claude-error)]/10 text-[var(--claude-error)]',
              message.level === 'warning' && 'bg-[var(--claude-warning)]/10 text-[var(--claude-warning)]',
              message.level === 'info' && 'bg-[var(--claude-background-secondary)] text-[var(--claude-foreground-muted)]'
            )}
          >
            {message.content}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <motion.div
      layout
      variants={messageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={cn(isLast && 'mb-2')}
    >
      {renderMessage()}
    </motion.div>
  );
});
