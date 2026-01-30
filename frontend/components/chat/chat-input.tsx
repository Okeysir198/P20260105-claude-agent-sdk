'use client';
import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Square, Loader2, MoreVertical, Minimize2, ImagePlus, X } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { ContentBlock, ImageContentBlock } from '@/types';
import { fileToImageBlock } from '@/lib/message-utils';

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
  const [images, setImages] = useState<ImageContentBlock[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    if (!disabled && (message.trim() || images.length > 0)) {
      // If there are images, create a multi-part message
      if (images.length > 0) {
        const contentBlocks: ContentBlock[] = [];

        // Add text block if there's text
        if (message.trim()) {
          contentBlocks.push({ type: 'text', text: message.trim() });
        }

        // Add image blocks (already in correct format)
        contentBlocks.push(...images);

        onSend(contentBlocks);
      } else {
        // Simple text message
        onSend(message.trim());
      }

      // Reset form
      setMessage('');
      setImages([]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // Process each file
    const newImages: ImageContentBlock[] = [];
    const MAX_SIZE = 5 * 1024 * 1024; // 5MB

    for (const file of Array.from(files)) {
      try {
        // Validate file type
        if (!file.type.startsWith('image/')) {
          console.error('Invalid file type:', file.type);
          continue;
        }

        // Validate file size
        if (file.size > MAX_SIZE) {
          console.error('File too large:', file.size);
          continue;
        }

        // Convert file to base64 using the utility
        const imageBlock = await fileToImageBlock(file);
        newImages.push(imageBlock);
      } catch (error) {
        console.error('Error processing image:', error);
      }
    }

    // Add to existing images
    setImages(prev => [...prev, ...newImages]);

    // Clear input to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    // Check for image items in clipboard
    const newImages: ImageContentBlock[] = [];
    const MAX_SIZE = 5 * 1024 * 1024; // 5MB

    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        e.preventDefault(); // Prevent default paste behavior

        const file = item.getAsFile();
        if (!file) continue;

        try {
          // Validate file size
          if (file.size > MAX_SIZE) {
            console.error('Pasted file too large:', file.size);
            continue;
          }

          // Convert clipboard image to base64
          const imageBlock = await fileToImageBlock(file);
          newImages.push(imageBlock);
        } catch (error) {
          console.error('Error processing pasted image:', error);
        }
      }
    }

    // Add pasted images to state
    if (newImages.length > 0) {
      setImages(prev => [...prev, ...newImages]);
    }
  };

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const hasContent = message.trim() || images.length > 0;

  return (
    <div className="bg-background px-2 sm:px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-background p-2 shadow-sm">
          {/* Image attachment button */}
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

          {/* Action buttons column */}
          <div className="flex flex-col items-center gap-1 shrink-0">
            {/* More options menu - shown when session has context */}
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

            {/* Send/Stop button */}
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

        {/* Image preview area */}
        {images.length > 0 && (
          <div className="mt-2 flex gap-2 overflow-x-auto">
            {images.map((image, index) => (
              <div key={index} className="relative h-20 w-20 rounded-lg border border-border overflow-hidden shrink-0">
                <img
                  src={image.source.type === 'url'
                    ? image.source.url
                    : `data:image;base64,${image.source.data}`
                  }
                  alt={`Attachment ${index + 1}`}
                  className="h-full w-full object-cover"
                />
                <button
                  type="button"
                  onClick={() => removeImage(index)}
                  className="absolute top-1 right-1 h-5 w-5 rounded-full bg-destructive text-white hover:bg-destructive/90 flex items-center justify-center"
                  disabled={disabled}
                  title="Remove image"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
