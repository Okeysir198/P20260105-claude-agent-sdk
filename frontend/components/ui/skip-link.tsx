'use client';

import { cn } from '@/lib/utils';

interface SkipLinkProps {
  /** Target element ID to skip to */
  targetId: string;
  /** Display text for the link */
  children: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Skip link for keyboard navigation accessibility.
 *
 * Allows keyboard users to skip navigation and jump directly to main content.
 * Hidden by default, visible on focus, compliant with WCAG 2.1 Level A.
 *
 * @example
 * ```tsx
 * <SkipLink targetId="main-content">Skip to main content</SkipLink>
 * <main id="main-content">...</main>
 * ```
 */
export function SkipLink({ targetId, children, className }: SkipLinkProps) {
  return (
    <a
      href={`#${targetId}`}
      className={cn(
        // Position off-screen by default
        'sr-only',
        // Show on focus with high visibility
        'focus:absolute focus:top-4 focus:left-4 focus:z-50',
        'focus:not-sr-only focus:px-4 focus:py-2',
        'focus:bg-claude-orange-600 focus:text-white',
        'focus:rounded-lg focus:shadow-lg',
        'focus:text-sm focus:font-medium',
        'transition-all',
        className
      )}
    >
      {children}
    </a>
  );
}
