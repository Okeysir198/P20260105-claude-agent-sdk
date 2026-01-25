'use client';
import type { ChatMessage } from '@/types';
import { formatTime } from '@/lib/utils';
import { User } from 'lucide-react';

interface UserMessageProps {
  message: ChatMessage;
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="group flex justify-end gap-3 py-2 px-4">
      <div className="max-w-[85%] space-y-1">
        <div className="rounded-lg bg-userMessage px-4 py-2.5 text-userMessageForeground shadow-sm">
          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <div className="flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-userIconBg border border-border/50">
        <User className="h-4 w-4 text-userMessageForeground" />
      </div>
    </div>
  );
}
