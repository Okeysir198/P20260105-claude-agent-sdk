'use client';

/**
 * Chat Input Component
 *
 * Auto-resizing textarea with send/interrupt button for chat interface.
 * Handles keyboard shortcuts and provides visual feedback for loading states.
 *
 * @module components/chat/chat-input
 */

import { useState, useRef, useCallback, useEffect, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Send, Square, Loader2 } from 'lucide-react';
import { useAutoResize } from '@/hooks/use-auto-resize';

interface ChatInputProps {
  /** Callback when user sends a message */
  onSend: (content: string) => Promise<void>;
  /** Callback to interrupt ongoing stream */
  onInterrupt: () => Promise<void>;
  /** Whether a request is being processed */
  isLoading: boolean;
  /** Whether a response is being streamed */
  isStreaming: boolean;
  /** Disable all input interactions */
  disabled?: boolean;
  /** Placeholder text for the textarea */
  placeholder?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Chat input component with auto-resizing textarea and action buttons.
 *
 * Features:
 * - Auto-resizing textarea (44px min, 200px max)
 * - Enter to send, Shift+Enter for newline
 * - Send button when idle
 * - Stop/interrupt button when streaming
 * - Loading spinner during processing
 * - Mobile-friendly touch targets
 *
 * @example
 * ```tsx
 * <ChatInput
 *   onSend={async (content) => console.log('Sending:', content)}
 *   onInterrupt={async () => console.log('Interrupted')}
 *   isLoading={false}
 *   isStreaming={false}
 * />
 * ```
 */
export function ChatInput({
  onSend,
  onInterrupt,
  isLoading,
  isStreaming,
  disabled = false,
  placeholder = 'Send a message...',
  className,
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isSending = useRef(false);

  // Auto-resize textarea based on content
  useAutoResize(textareaRef, value, 28, 200);

  // Focus textarea on mount (desktop only)
  useEffect(() => {
    // Check if device is likely desktop (no touch support or large screen)
    const isDesktop = !('ontouchstart' in window) || window.innerWidth >= 1024;
    if (isDesktop && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  // Handle sending message
  const handleSend = useCallback(async () => {
    const trimmedValue = value.trim();
    if (!trimmedValue || isLoading || disabled || isSending.current) return;

    isSending.current = true;
    setValue('');

    try {
      await onSend(trimmedValue);
    } finally {
      isSending.current = false;
      // Refocus textarea after sending with a small delay to ensure DOM updates
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 10);
    }
  }, [value, isLoading, disabled, onSend]);

  // Handle interrupt
  const handleInterrupt = useCallback(async () => {
    if (!isStreaming) return;
    await onInterrupt();
  }, [isStreaming, onInterrupt]);

  // Keyboard event handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter without Shift sends message
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (isStreaming) {
          handleInterrupt();
        } else {
          handleSend();
        }
      }
    },
    [isStreaming, handleSend, handleInterrupt]
  );

  // Determine button state and content
  const isDisabled = disabled || isLoading;
  const showStopButton = isStreaming;
  const canSend = value.trim().length > 0 && !isLoading && !disabled;

  return (
    <div
      className={cn(
        'flex items-end gap-3',
        'p-3',
        'bg-surface-secondary',
        'border border-border-primary',
        'rounded-2xl',
        'shadow-soft',
        className
      )}
    >
      {/* Textarea - borderless inside container */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={isDisabled}
        rows={1}
        className={cn(
          'flex-1 resize-none',
          'bg-transparent',
          'border-none outline-none',
          'px-2 py-1',
          'text-base text-text-primary',
          'placeholder:text-text-tertiary',
          'focus:outline-none focus:ring-0 focus:border-none',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'min-h-[28px] max-h-[200px]'
        )}
        style={{
          height: '28px',
          boxShadow: 'none',
        }}
        aria-label="Message input"
      />

      {/* Action button */}
      {showStopButton ? (
        <Button
          type="button"
          variant="destructive"
          size="icon"
          onClick={handleInterrupt}
          className={cn(
            'h-9 w-9 rounded-xl flex-shrink-0',
            'transition-all duration-200'
          )}
          aria-label="Stop generating"
        >
          <Square className="h-4 w-4 fill-current" />
        </Button>
      ) : (
        <Button
          type="button"
          variant="default"
          size="icon"
          onClick={handleSend}
          disabled={!canSend}
          className={cn(
            'h-9 w-9 rounded-xl flex-shrink-0',
            'bg-claude-orange-600 hover:bg-claude-orange-700',
            'transition-all duration-200',
            canSend && 'shadow-md hover:shadow-lg',
            !canSend && 'opacity-40'
          )}
          aria-label={isLoading ? 'Sending...' : 'Send message'}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      )}
    </div>
  );
}
