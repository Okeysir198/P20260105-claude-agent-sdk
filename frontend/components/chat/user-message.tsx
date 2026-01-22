'use client';

import { memo, useState } from 'react';
import type { UserMessage as UserMessageType } from '@/types/messages';
import { cn, formatTime } from '@/lib/utils';
import { User } from 'lucide-react';
import { MessageActions } from './message-actions';

interface UserMessageProps {
  message: UserMessageType;
  className?: string;
  onDelete?: (messageId: string) => void;
}

function UserAvatar({ className }: { className?: string }): React.ReactElement {
  return (
    <div className={cn(
      'flex-shrink-0 w-8 h-8 rounded-full',
      'bg-muted',
      'border border-border',
      'flex items-center justify-center',
      className
    )}>
      <User className="w-4 h-4 text-muted-foreground" />
    </div>
  );
}

export const UserMessage = memo(function UserMessage({
  message,
  className,
  onDelete
}: UserMessageProps): React.ReactElement {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className={cn('flex justify-end gap-3 group/message', className)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex flex-col items-end gap-2 max-w-[85%]">
        {/* Message bubble with actions */}
        <div className="relative flex items-end justify-end gap-2">
          {/* Message content */}
          <div
            className={cn(
              'px-5 py-3',
              'bg-primary text-primary-foreground',
              'rounded-2xl rounded-tr-sm',
              'shadow-soft',
              'max-w-full'
            )}
          >
            <p className="whitespace-pre-wrap break-normal text-base leading-relaxed">
              {message.content}
            </p>
          </div>

          {/* Message actions - show on hover */}
          <div className="absolute -top-10 right-0 opacity-0 group-hover/message:opacity-100 transition-opacity duration-200">
            <MessageActions
              content={message.content}
              messageId={message.id}
              onDelete={onDelete}
            />
          </div>
        </div>

        {/* Timestamp */}
        <div
          className={cn(
            'flex justify-end transition-opacity duration-200',
            isHovered ? 'opacity-100' : 'opacity-0'
          )}
        >
          <span className="text-[10px] text-muted-foreground">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>

      <UserAvatar />
    </div>
  );
});
