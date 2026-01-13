'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import type { AssistantMessage as AssistantMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';
import { TypingIndicator } from './typing-indicator';
import { messageItemVariants } from '@/lib/animations';

interface AssistantMessageProps {
  message: AssistantMessageType;
  className?: string;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

/**
 * Claude avatar component with signature orange styling.
 */
function ClaudeAvatar({ className }: { className?: string }) {
  return (
    <div className={cn(
      'flex-shrink-0 w-8 h-8',
      'rounded-full',
      'bg-gradient-to-br from-claude-orange-100 to-claude-orange-200',
      'dark:from-claude-orange-900/50 dark:to-claude-orange-800/50',
      'flex items-center justify-center',
      'shadow-soft',
      className
    )}>
      <svg
        className="w-4 h-4 text-claude-orange-600 dark:text-claude-orange-400"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="12" cy="12" r="3" fill="currentColor" />
        <path
          d="M12 5C8.134 5 5 8.134 5 12M12 5C15.866 5 19 8.134 19 12M12 5V3M19 12C19 15.866 15.866 19 12 19M19 12H21M12 19C8.134 19 5 15.866 5 12M12 19V21M5 12H3"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  className
}: AssistantMessageProps) {
  return (
    <motion.div
      variants={messageItemVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={cn('flex justify-start gap-3', className)}
    >
      {/* Avatar */}
      <ClaudeAvatar />

      {/* Message content */}
      <div className={cn(
        'max-w-[75%]',
        'px-4 py-3',
        'bg-surface-secondary',
        'border border-border-primary',
        'rounded-2xl rounded-tl-sm',
        'shadow-soft'
      )}>
        {/* Label with timestamp */}
        <div className="flex items-center justify-between gap-3 mb-1">
          <span className="text-xs font-medium text-claude-orange-500 dark:text-claude-orange-400">Claude</span>
          <span className="text-xs text-text-tertiary">{formatTime(message.timestamp)}</span>
        </div>

        {/* Content */}
        <div className="prose-claude text-text-primary">
          {message.content ? (
            <div
              className="whitespace-pre-wrap break-words text-base leading-relaxed"
              dangerouslySetInnerHTML={{
                __html: formatMarkdown(message.content)
              }}
            />
          ) : message.isStreaming ? (
            <TypingIndicator />
          ) : null}

          {/* Streaming cursor */}
          {message.isStreaming && message.content && (
            <span className="inline-block w-0.5 h-5 ml-0.5 bg-claude-orange-500 animate-typing rounded-full" />
          )}
        </div>
      </div>
    </motion.div>
  );
});

/**
 * Simple markdown formatting for common patterns.
 * For full markdown support, consider using a library like marked or react-markdown.
 */
function formatMarkdown(content: string): string {
  return content
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Code blocks (triple backticks)
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    // Inline code (single backticks)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold (**text**)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Italic (*text*)
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // Links [text](url)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    // Line breaks
    .replace(/\n/g, '<br />');
}
