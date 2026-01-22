'use client';

import { memo, useState, useCallback } from 'react';
import type { SessionInfo } from '@/types/sessions';
import { cn } from '@/lib/utils';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SwipeActions } from '@/components/mobile';

interface SessionItemProps {
  session: SessionInfo;
  isActive: boolean;
  isSelected: boolean;
  onSelect: () => void;
  onDelete?: () => void;
}

/**
 * Truncates a string to a specified length with ellipsis.
 */
function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + '...';
}

/**
 * Formats a date string to a relative or short format.
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

export const SessionItem = memo(function SessionItem({
  session,
  isActive,
  isSelected,
  onSelect,
  onDelete,
}: SessionItemProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = useCallback(
    async () => {
      if (!onDelete || isDeleting) return;

      setIsDeleting(true);
      try {
        await onDelete();
      } finally {
        setIsDeleting(false);
      }
    },
    [onDelete, isDeleting]
  );

  const handleDeleteClick = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      await handleDelete();
    },
    [handleDelete]
  );

  // Display title, preview, or truncated session ID
  const displayTitle = session.title || session.preview || truncate(session.id, 16);
  const displayId = truncate(session.id, 8);

  const itemContent = (
    <div
      role="option"
      tabIndex={0}
      aria-selected={isSelected}
      aria-label={`Session: ${displayTitle}, ${formatDate(session.last_activity)}`}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        'group relative flex items-center gap-3 px-3 py-2.5 md:py-2.5 rounded-xl cursor-pointer',
        'transition-all duration-150',
        'hover:bg-surface-primary',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-claude-orange-500',
        isSelected && 'bg-claude-orange-50 dark:bg-claude-orange-900/20',
        isSelected && 'border border-claude-orange-200 dark:border-claude-orange-800'
      )}
    >
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'text-sm font-medium truncate',
              isSelected
                ? 'text-text-primary'
                : 'text-text-secondary'
            )}
          >
            {displayTitle}
          </span>
          {isActive && (
            <span
              className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-success-500 animate-pulse"
              aria-label="Active session"
            />
          )}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-text-tertiary mt-0.5">
          <span className="truncate font-mono" aria-label={`Session ID: ${session.id}`}>{displayId}</span>
          <span className="flex-shrink-0" aria-hidden="true">·</span>
          <span className="flex-shrink-0">{formatDate(session.last_activity)}</span>
        </div>
      </div>

      {/* Delete button (visible on hover on desktop, always on mobile if swiped) */}
      {onDelete && (
        <Button
          variant="ghost"
          size="icon"
          onClick={handleDeleteClick}
          disabled={isDeleting}
          className={cn(
            'hidden md:flex flex-shrink-0 h-7 w-7 rounded-lg',
            'opacity-0 group-hover:opacity-100 transition-opacity',
            'text-text-tertiary hover:text-error-600 hover:bg-error-50 dark:hover:bg-error-900/20',
            isDeleting && 'opacity-50'
          )}
          aria-label={`Delete session: ${displayTitle}`}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      )}
    </div>
  );

  // Wrap with swipe actions on mobile
  if (onDelete) {
    return (
      <SwipeActions onDelete={handleDelete}>
        {itemContent}
      </SwipeActions>
    );
  }

  return itemContent;
});
