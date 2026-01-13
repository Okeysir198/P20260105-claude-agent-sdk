'use client';

import { memo, useState, useCallback } from 'react';
import type { SessionInfo } from '@/types/sessions';
import { cn } from '@/lib/utils';
import { MessageSquare, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

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
  const [isHovered, setIsHovered] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
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

  // Display title, preview, or truncated session ID
  const displayTitle = session.title || session.preview || truncate(session.id, 16);
  const displayId = truncate(session.id, 8);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        'group relative flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors',
        'hover:bg-[var(--claude-background-secondary)]',
        isSelected && 'bg-[var(--claude-background-secondary)]',
        isSelected && 'ring-1 ring-[var(--claude-primary)]'
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-md',
          isActive
            ? 'bg-[var(--claude-success)]/10 text-[var(--claude-success)]'
            : 'bg-[var(--claude-border)]/50 text-[var(--claude-foreground-muted)]'
        )}
      >
        <MessageSquare className="w-4 h-4" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'text-sm font-medium truncate',
              isSelected
                ? 'text-[var(--claude-foreground)]'
                : 'text-[var(--claude-foreground-muted)]'
            )}
          >
            {displayTitle}
          </span>
          {isActive && (
            <span className="flex-shrink-0 w-2 h-2 rounded-full bg-[var(--claude-success)]" />
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--claude-foreground-muted)]">
          <span className="truncate">{displayId}</span>
          <span className="flex-shrink-0">-</span>
          <span className="flex-shrink-0">{formatDate(session.last_activity)}</span>
        </div>
      </div>

      {/* Delete button (visible on hover) */}
      {onDelete && (isHovered || isDeleting) && (
        <Button
          variant="ghost"
          size="icon"
          onClick={handleDelete}
          disabled={isDeleting}
          className={cn(
            'flex-shrink-0 h-7 w-7',
            'opacity-0 group-hover:opacity-100 transition-opacity',
            'hover:bg-[var(--claude-error)]/10 hover:text-[var(--claude-error)]',
            isDeleting && 'opacity-50'
          )}
          aria-label="Delete session"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      )}
    </div>
  );
});
