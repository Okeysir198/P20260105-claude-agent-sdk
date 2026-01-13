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
  useAutoResize(textareaRef, value, 44, 200);

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
    try {
      setValue('');
      await onSend(trimmedValue);
    } finally {
      isSending.current = false;
      // Refocus textarea after sending
      textareaRef.current?.focus();
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
        'relative flex items-end gap-2 p-4 border-t border-[var(--claude-border)] bg-[var(--claude-background)]',
        className
      )}
    >
      {/* Textarea container */}
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isDisabled}
          rows={1}
          className={cn(
            'w-full resize-none rounded-lg border border-[var(--claude-border)] bg-[var(--claude-background-secondary)] px-4 py-3 text-sm text-[var(--claude-foreground)]',
            'placeholder:text-[var(--claude-foreground-muted)]',
            'focus:outline-none focus:ring-2 focus:ring-[var(--claude-primary)] focus:border-transparent',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'transition-all duration-200',
            // Ensure minimum height matches auto-resize settings
            'min-h-[44px]'
          )}
          style={{
            // Initial height set by CSS, will be overridden by useAutoResize
            height: '44px',
          }}
          aria-label="Message input"
        />
      </div>

      {/* Action button */}
      <div className="flex-shrink-0">
        {showStopButton ? (
          // Stop/Interrupt button when streaming
          <Button
            type="button"
            variant="destructive"
            size="icon"
            onClick={handleInterrupt}
            className={cn(
              'h-11 w-11',
              // Larger touch target on mobile
              'sm:h-10 sm:w-10',
              'transition-all duration-200'
            )}
            aria-label="Stop generating"
          >
            <Square className="h-4 w-4 fill-current" />
          </Button>
        ) : (
          // Send button when not streaming
          <Button
            type="button"
            variant="default"
            size="icon"
            onClick={handleSend}
            disabled={!canSend}
            className={cn(
              'h-11 w-11',
              // Larger touch target on mobile
              'sm:h-10 sm:w-10',
              'transition-all duration-200',
              // Visual feedback when can send
              canSend && 'shadow-md hover:shadow-lg'
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
    </div>
  );
}
