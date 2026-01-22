'use client';

import { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

interface LiveRegionProps {
  /** Content to announce to screen readers */
  children: React.ReactNode;
  /** Politeness level: 'polite' waits for idle, 'assertive' interrupts immediately */
  politeness?: 'polite' | 'assertive';
  /** Whether this is a live region (true) or status message (false) */
  isLive?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * ARIA live region for screen reader announcements.
 *
 * Used to announce dynamic content changes to screen reader users.
 * Content is visually hidden but announced by assistive technologies.
 *
 * Live regions should be used for:
 * - Status messages (loading, success, errors)
 * - Typing indicators
 * - New message notifications
 * - Form validation feedback
 *
 * @example
 * ```tsx
 * <LiveRegion politeness="polite">
 *   {isLoading && 'Loading conversations...'}
 *   {error && `Error: ${error}`}
 * </LiveRegion>
 * ```
 */
export function LiveRegion({
  children,
  politeness = 'polite',
  isLive = true,
  className,
}: LiveRegionProps) {
  const regionRef = useRef<HTMLDivElement | null>(null);

  // Track previous content to detect changes
  const previousContentRef = useRef<string>('');

  useEffect(() => {
    const currentContent = String(children ?? '').trim();

    // Only announce if content actually changed
    if (currentContent && currentContent !== previousContentRef.current) {
      previousContentRef.current = currentContent;

      // Force screen reader to announce by clearing and resetting content
      if (regionRef.current) {
        regionRef.current.textContent = '';
        setTimeout(() => {
          if (regionRef.current) {
            regionRef.current.textContent = currentContent;
          }
        }, 50);
      }
    }
  }, [children]);

  return (
    <div
      ref={regionRef}
      role={isLive ? 'status' : undefined}
      aria-live={isLive ? politeness : undefined}
      aria-atomic="true"
      className={cn('sr-only', className)}
    >
      {children}
    </div>
  );
}

interface VisuallyHiddenProps {
  children: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Visually hide content while keeping it accessible to screen readers.
 *
 * Use for labels, instructions, or context needed by screen reader users
 * but not needed visually in the UI.
 *
 * @example
 * ```tsx
 * <VisuallyHidden>
 *   Press Enter to send, Shift+Enter for new line
 * </VisuallyHidden>
 * ```
 */
export function VisuallyHidden({ children, className }: VisuallyHiddenProps) {
  return (
    <span className={cn('sr-only', className)}>{children}</span>
  );
}
