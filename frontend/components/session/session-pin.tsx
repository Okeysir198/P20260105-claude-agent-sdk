'use client';

import { Pin, PinOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface SessionPinProps {
  isPinned: boolean;
  onToggle: () => void;
  className?: string;
  size?: 'sm' | 'md';
}

export function SessionPin({ isPinned, onToggle, className, size = 'sm' }: SessionPinProps) {
  const sizeClasses = size === 'sm' ? 'h-6 w-6' : 'h-8 w-8';

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      className={cn(
        sizeClasses,
        'text-text-tertiary hover:text-claude-orange-600',
        'transition-colors duration-200',
        isPinned && 'text-claude-orange-600',
        className
      )}
      aria-label={isPinned ? 'Unpin session' : 'Pin session'}
      title={isPinned ? 'Pinned' : 'Pin to top'}
    >
      {isPinned ? (
        <Pin className="h-3.5 w-3.5 fill-current" />
      ) : (
        <PinOff className="h-3.5 w-3.5" />
      )}
    </Button>
  );
}
