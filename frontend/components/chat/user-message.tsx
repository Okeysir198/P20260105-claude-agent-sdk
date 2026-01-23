'use client';
import type { ChatMessage } from '@/types';
import { formatTime } from '@/lib/utils';
import { User } from 'lucide-react';

interface UserMessageProps {
  message: ChatMessage;
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="group flex justify-end gap-3 p-4">
      <div className="max-w-[80%] space-y-1">
        <div
          className="rounded-lg px-4 py-2"
          style={{ backgroundColor: 'hsl(var(--user-message))', color: 'hsl(var(--user-message-foreground))' }}
        >
          <p className="text-sm leading-relaxed">{message.content}</p>
        </div>
        <div className="flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded"
        style={{ backgroundColor: 'hsl(var(--user-message))' }}
      >
        <User className="h-5 w-5" style={{ color: 'hsl(var(--user-message-foreground))' }} />
      </div>
    </div>
  );
}
