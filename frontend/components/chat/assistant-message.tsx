'use client';

import { memo } from 'react';
import type { AssistantMessage as AssistantMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';
import { TypingIndicator } from './typing-indicator';

interface AssistantMessageProps {
  message: AssistantMessageType;
  className?: string;
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  className
}: AssistantMessageProps) {
  return (
    <div className={cn(
      'max-w-[80%] mr-auto',
      'flex gap-3',
      className
    )}>
      {/* Avatar */}
      <div className={cn(
        'flex-shrink-0 w-8 h-8',
        'rounded-full',
        'bg-claude-orange-100 dark:bg-claude-orange-900',
        'flex items-center justify-center',
        'text-claude-orange-600 dark:text-claude-orange-400'
      )}>
        <svg
          className="w-5 h-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      </div>

      {/* Message content */}
      <div className={cn(
        'flex-1 px-4 py-3',
        'bg-surface-secondary',
        'border border-border-primary',
        'rounded-2xl rounded-tl-md',
        'shadow-soft'
      )}>
        <div className="prose-claude">
          {message.content ? (
            <div
              className="whitespace-pre-wrap break-words"
              dangerouslySetInnerHTML={{
                __html: formatMarkdown(message.content)
              }}
            />
          ) : message.isStreaming ? (
            <TypingIndicator />
          ) : null}

          {/* Streaming cursor */}
          {message.isStreaming && message.content && (
            <span className="inline-block w-2 h-4 ml-0.5 bg-claude-orange-500 animate-typing" />
          )}
        </div>
      </div>
    </div>
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
