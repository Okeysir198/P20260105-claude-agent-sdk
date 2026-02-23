'use client';
import type { ChatMessage, ImageContentBlock, AudioContentBlock, VideoContentBlock, FileContentBlock } from '@/types';
import { formatTime } from '@/lib/utils';
import { User } from 'lucide-react';
import { useMemo, useCallback } from 'react';
import { normalizeContent } from '@/lib/content-utils';
import { InlineImage, InlineAudioPlayer, InlineVideoPlayer, InlineFileCard } from './media';
import { useLightboxStore } from '@/lib/store/lightbox-store';

interface UserMessageProps {
  message: ChatMessage;
}

export function UserMessage({ message }: UserMessageProps) {
  const { textBlocks, imageBlocks, audioBlocks, videoBlocks, fileBlocks } = useMemo(() => {
    const blocks = normalizeContent(message.content);
    const text: Array<{ type: 'text'; text: string }> = [];
    const images: ImageContentBlock[] = [];
    const audio: AudioContentBlock[] = [];
    const video: VideoContentBlock[] = [];
    const files: FileContentBlock[] = [];

    for (const block of blocks) {
      switch (block.type) {
        case 'text':
          text.push(block as { type: 'text'; text: string });
          break;
        case 'image':
          images.push(block as ImageContentBlock);
          break;
        case 'audio':
          audio.push(block as AudioContentBlock);
          break;
        case 'video':
          video.push(block as VideoContentBlock);
          break;
        case 'file':
          files.push(block as FileContentBlock);
          break;
      }
    }

    return { textBlocks: text, imageBlocks: images, audioBlocks: audio, videoBlocks: video, fileBlocks: files };
  }, [message.content]);

  const hasMedia = imageBlocks.length > 0 || audioBlocks.length > 0 || videoBlocks.length > 0 || fileBlocks.length > 0;

  const imageUrls = useMemo(() => {
    return imageBlocks.map((block) => {
      return block.source.type === 'url'
        ? block.source.url!
        : `data:image/jpeg;base64,${block.source.data}`;
    });
  }, [imageBlocks]);

  const openLightbox = useLightboxStore((s) => s.open);

  const handleImageZoom = useCallback(
    (src: string) => {
      const idx = imageUrls.indexOf(src);
      openLightbox(imageUrls, idx >= 0 ? idx : 0);
    },
    [imageUrls, openLightbox],
  );

  return (
    <div className="group flex justify-end gap-2 sm:gap-3 py-2 px-2 sm:px-4">
      <div className="max-w-[85%] space-y-2">
        {hasMedia && (
          <div className="flex flex-wrap gap-2 justify-end">
            {imageBlocks.map((block, index) => {
              const imageUrl = block.source.type === 'url'
                ? block.source.url
                : `data:image/jpeg;base64,${block.source.data}`;
              return (
                <InlineImage
                  key={`image-${index}`}
                  src={imageUrl!}
                  alt={`Uploaded image ${index + 1}`}
                  onClickZoom={handleImageZoom}
                />
              );
            })}
            {audioBlocks.map((block, index) => (
              <InlineAudioPlayer
                key={`audio-${index}`}
                src={block.source.url}
                filename={block.filename}
                mimeType={block.source.mime_type}
              />
            ))}
            {videoBlocks.map((block, index) => (
              <InlineVideoPlayer
                key={`video-${index}`}
                src={block.source.url}
                filename={block.filename}
                mimeType={block.source.mime_type}
              />
            ))}
            {fileBlocks.map((block, index) => (
              <InlineFileCard
                key={`file-${index}`}
                filename={block.filename}
                url={block.source.url}
                size={block.size}
                mimeType={block.source.mime_type}
              />
            ))}
          </div>
        )}

        {textBlocks.length > 0 && (
          <div className="rounded-lg bg-userMessage px-4 py-2.5 text-userMessageForeground shadow-sm">
            <p className="text-sm sm:text-base leading-relaxed whitespace-pre-wrap break-words">
              {textBlocks.map(block => block.text).join('')}
            </p>
          </div>
        )}

        <div className="flex justify-end opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-userIconBg border border-border/50">
        <User className="h-4 w-4 text-userMessageForeground" />
      </div>
    </div>
  );
}
