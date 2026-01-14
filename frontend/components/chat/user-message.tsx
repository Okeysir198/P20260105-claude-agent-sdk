'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import type { UserMessage as UserMessageType } from '@/types/messages';
import { cn, formatTime } from '@/lib/utils';
import { messageItemVariants } from '@/lib/animations';

interface UserMessageProps {
  message: UserMessageType;
  className?: string;
}

export const UserMessage = memo(function UserMessage({
  message,
  className
}: UserMessageProps): React.ReactElement {
  return (
    <motion.div
      variants={messageItemVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={cn('flex justify-end', className)}
    >
      <div className={cn(
        'max-w-[75%] px-4 py-3',
        'bg-claude-orange-500 text-white',
        'rounded-2xl rounded-br-sm shadow-soft'
      )}>
        <div className="flex items-center justify-between gap-3 mb-1">
          <span className="text-xs font-medium text-white/80">You</span>
          <span className="text-xs text-white/60">{formatTime(message.timestamp)}</span>
        </div>
        <p className="whitespace-pre-wrap break-words text-base leading-relaxed">
          {message.content}
        </p>
      </div>
    </motion.div>
  );
});
