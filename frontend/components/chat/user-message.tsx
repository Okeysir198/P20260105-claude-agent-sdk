'use client';
import type { ChatMessage, ContentBlock } from '@/types';
import { formatTime } from '@/lib/utils';
import { User } from 'lucide-react';
import { useMemo } from 'react';
import { normalizeContent, extractText } from '@/lib/content-utils';

interface UserMessageProps {
  message: ChatMessage;
}

export function UserMessage({ message }: UserMessageProps) {
  // Normalize content to ContentBlock array
  const contentBlocks = useMemo(() => {
    return normalizeContent(message.content);
  }, [message.content]);

  // Separate text and image blocks
  const textBlocks = useMemo(() => {
    return contentBlocks.filter((block): block is { type: 'text'; text: string } =>
      block.type === 'text'
    );
  }, [contentBlocks]);

  const imageBlocks = useMemo(() => {
    return contentBlocks.filter((block) => block.type === 'image');
  }, [contentBlocks]);

  return (
    <div className="group flex justify-end gap-2 sm:gap-3 py-2 px-2 sm:px-4">
      <div className="max-w-[85%] space-y-2">
        {/* Display images first */}
        {imageBlocks.length > 0 && (
          <div className="flex flex-wrap gap-2 justify-end">
            {imageBlocks.map((block, index) => {
              const imageUrl = block.source.type === 'url'
                ? block.source.url
                : `data:image/jpeg;base64,${block.source.data}`;
              return (
                <img
                  key={`image-${index}`}
                  src={imageUrl}
                  alt={`Uploaded image ${index + 1}`}
                  className="max-w-[200px] max-h-[200px] rounded-lg border border-border/20 object-contain"
                />
              );
            })}
          </div>
        )}

        {/* Display text content */}
        {textBlocks.length > 0 && (
          <div className="rounded-lg bg-userMessage px-4 py-2.5 text-userMessageForeground shadow-sm">
            <p className="text-sm sm:text-base leading-relaxed whitespace-pre-wrap break-words">
              {textBlocks.map(block => block.text).join('')}
            </p>
          </div>
        )}

        {/* Timestamp */}
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
