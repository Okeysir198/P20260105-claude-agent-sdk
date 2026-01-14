'use client';

import { memo, useState } from 'react';
import type { UserMessage as UserMessageType } from '@/types/messages';
import { cn, formatTime } from '@/lib/utils';
import { User } from 'lucide-react';

interface UserMessageProps {
  message: UserMessageType;
  className?: string;
}

function UserAvatar({ className }: { className?: string }): React.ReactElement {
  return (
    <div className={cn(
      'flex-shrink-0 w-8 h-8 rounded-lg',
      'bg-surface-tertiary dark:bg-surface-inverse/20',
      'border border-border-primary',
      'flex items-center justify-center',
      className
    )}>
      <User className="w-4 h-4 text-text-secondary" />
    </div>
  );
}

export const UserMessage = memo(function UserMessage({
  message,
  className
}: UserMessageProps): React.ReactElement {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div className={cn('flex justify-end gap-3', className)}>
      <div className="flex flex-col items-end">
        <div
          className={cn(
            'max-w-[85%] px-5 py-3',
            'bg-surface-tertiary dark:bg-surface-inverse/10',
            'text-text-primary',
            'border border-border-primary',
            'rounded-lg shadow-soft'
          )}
        >
          <p className="whitespace-pre-wrap break-normal text-base leading-relaxed pr-2">
            {message.content}
          </p>
        </div>
        <div className="flex justify-end mt-1">
          <span className="text-[10px] text-text-tertiary">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
      <UserAvatar />
    </div>
  );
});
