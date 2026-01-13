'use client';

import { memo } from 'react';
import type { UserMessage as UserMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';

interface UserMessageProps {
  message: UserMessageType;
  className?: string;
}

export const UserMessage = memo(function UserMessage({ message, className }: UserMessageProps) {
  return (
    <div className={cn(
      'max-w-[80%] ml-auto px-4 py-3',
      'bg-claude-orange-600',
      'text-white',
      'rounded-2xl rounded-br-md',
      'shadow-soft',
      className
    )}>
      <p className="whitespace-pre-wrap break-words font-serif">
        {message.content}
      </p>
    </div>
  );
});
