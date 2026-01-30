'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Square, Loader2, MoreVertical, Minimize2, ImagePlus } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { ContentBlock, TextContentBlock } from '@/types';
import { useImageUpload } from '@/hooks/use-image-upload';
import { ImageAttachment } from './image-attachment';

interface ChatInputProps {
  onSend: (message: string | ContentBlock[]) => void;
  onCancel?: () => void;
  onCompact?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  isCancelling?: boolean;
  isCompacting?: boolean;
  canCompact?: boolean;
}

export function ChatInput({
  onSend,
  onCancel,
  onCompact,
  disabled,
  isStreaming,
  isCancelling,
  isCompacting,
  canCompact
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    images,
    fileInputRef,
    addImages,
    removeImage,
    clearImages,
    hasImages
  } = useImageUpload();

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  function buildContent(): string | ContentBlock[] {
    const trimmed = message.trim();

    if (!hasImages) {
      return trimmed;
    }

    const blocks: ContentBlock[] = [];

    if (trimmed) {
      const textBlock: TextContentBlock = { type: 'text', text: trimmed };
      blocks.push(textBlock);
    }

    blocks.push(...images);

    return blocks;
  }

  function handleSubmit() {
    if (disabled || (!message.trim() && !hasImages)) {
      return;
    }

    onSend(buildContent());
    setMessage('');
    clearImages();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  async function handleImageSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (files && files.length > 0) {
      await addImages(Array.from(files));
    }
  }

  async function handlePaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const items = e.clipboardData?.items;
    if (!items) return;

    const imageFiles: File[] = [];

    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          imageFiles.push(file);
        }
      }
    }

    if (imageFiles.length > 0) {
      await addImages(imageFiles);
    }
  }

  const hasContent = message.trim() || hasImages;

  return (
    <div className="bg-background px-2 sm:px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-background p-2 shadow-sm">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-lg text-muted-foreground hover:text-foreground shrink-0"
            disabled={disabled}
            onClick={() => fileInputRef.current?.click()}
            title="Upload image"
          >
            <ImagePlus className="h-5 w-5" />
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png, image/jpeg, image/gif, image/webp"
            multiple
            className="hidden"
            onChange={handleImageSelect}
          />

          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder="Message Claude..."
            className="chat-textarea flex-1 min-h-[60px] max-h-[200px] resize-none bg-transparent px-3 py-2 text-base md:text-sm placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
            disabled={disabled}
          />

          <div className="flex flex-col items-center gap-1 shrink-0">
            {canCompact && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 rounded-lg text-muted-foreground hover:text-foreground"
                    disabled={disabled}
                  >
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem
                    onClick={onCompact}
                    disabled={isCompacting}
                    className="gap-2"
                  >
                    {isCompacting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Minimize2 className="h-4 w-4" />
                    )}
                    <span>Compact context</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {isStreaming ? (
              <Button
                onClick={onCancel}
                disabled={isCancelling}
                size="icon"
                className="h-10 w-10 rounded-xl bg-destructive hover:bg-destructive/90 text-white"
              >
                {isCancelling ? <Loader2 className="h-5 w-5 animate-spin" /> : <Square className="h-5 w-5" />}
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={!hasContent || disabled}
                size="icon"
                className="h-10 w-10 rounded-xl bg-primary text-white hover:bg-primary-hover disabled:opacity-50"
              >
                <Send className="h-5 w-5" />
              </Button>
            )}
          </div>
        </div>

        {hasImages && (
          <div className="mt-2 flex gap-2 overflow-x-auto">
            {images.map((image, index) => (
              <ImageAttachment
                key={index}
                image={image}
                index={index}
                onRemove={removeImage}
                disabled={disabled}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
