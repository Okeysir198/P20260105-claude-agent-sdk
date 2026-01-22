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
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Send, Square, Loader2 } from 'lucide-react';
import { useAutoResize } from '@/hooks/use-auto-resize';
import { buttonMicroVariants } from '@/lib/animations';

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
  useAutoResize(textareaRef, value, 40, 200);

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
        'flex items-end gap-2 md:gap-3',
        'p-3 md:p-4 pb-safe-4',
        'bg-surface-secondary',
        'border border-border-primary',
        'rounded-2xl',
        'shadow-soft',
        'transition-all duration-200',
        className
      )}
      role="group"
      aria-label="Message composition"
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
          'px-3 py-3 md:py-2',
          'text-base md:text-sm',
          'text-text-primary',
          'placeholder:text-text-tertiary',
          'focus:outline-none focus:ring-0 focus:border-none',
          'focus-visible:ring-2 focus-visible:ring-claude-orange-500 focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'min-h-[44px] md:min-h-[40px] max-h-[200px]',
          'transition-all duration-200'
        )}
        style={{
          height: typeof window !== 'undefined' && window.innerWidth < 768 ? '44px' : '40px',
          boxShadow: 'none',
        }}
        aria-label="Message input"
        aria-describedby="chat-input-help"
      />

      {/* Action button with micro-interactions - larger touch target on mobile */}
      {showStopButton ? (
        <motion.button
          type="button"
          onClick={handleInterrupt}
          className={cn(
            'h-11 w-11 md:h-9 md:w-9 rounded-xl flex-shrink-0',
            'flex items-center justify-center',
            'bg-black dark:bg-white',
            'border-2 border-black dark:border-white',
            'text-white dark:text-black',
            'hover:bg-black/90 dark:hover:bg-white/90',
            'transition-colors duration-200'
          )}
          variants={buttonMicroVariants}
          initial="idle"
          whileHover="hover"
          whileTap="tap"
          aria-label="Stop generating response"
          title="Stop generating (Enter)"
        >
          <Square className="h-4 w-4" />
        </motion.button>
      ) : (
        <motion.button
          type="button"
          onClick={handleSend}
          disabled={!canSend}
          className={cn(
            'h-11 w-11 md:h-9 md:w-9 rounded-xl flex-shrink-0',
            'flex items-center justify-center',
            'bg-claude-orange-600 hover:bg-claude-orange-700',
            'text-white',
            'transition-colors duration-200',
            canSend && 'shadow-md',
            !canSend && 'opacity-40 cursor-not-allowed'
          )}
          variants={buttonMicroVariants}
          initial="idle"
          whileHover={canSend ? 'hover' : 'idle'}
          whileTap={canSend ? 'tap' : 'idle'}
          aria-label={isLoading ? 'Sending message...' : canSend ? 'Send message' : 'Enter a message to send'}
          title={canSend ? 'Send message (Enter)' : 'Type a message first'}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
        </motion.button>
      )}

      {/* Hidden help text for screen readers */}
      <span id="chat-input-help" className="sr-only">
        Press Enter to send message, Shift+Enter for new line
      </span>
    </div>
  );
}
