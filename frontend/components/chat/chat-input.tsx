'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Square, Loader2, Plus, Mic, Image as ImageIcon, FileText, X } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import type { ContentBlock, TextContentBlock, ImageContentBlock } from '@/types';
import { useImageUpload } from '@/hooks/use-image-upload';
import { ImageAttachment } from './image-attachment';
import { useFileUpload } from '@/hooks/use-files';
import { useChatStore } from '@/lib/store/chat-store';
import { toast } from 'sonner';

interface FileAttachment {
  id: string;
  file: File;
  preview?: string;
}

interface ChatInputProps {
  onSend: (message: string | ContentBlock[]) => void;
  onCancel?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  isCancelling?: boolean;
}

export function ChatInput({
  onSend,
  onCancel,
  disabled,
  isStreaming,
  isCancelling,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [attachmentMenuOpen, setAttachmentMenuOpen] = useState(false);
  const [fileAttachments, setFileAttachments] = useState<FileAttachment[]>([]);

  const sessionId = useChatStore((state) => state.sessionId);

  const {
    images,
    fileInputRef,
    addImages,
    removeImage,
    clearImages,
    hasImages
  } = useImageUpload();

  const { uploadFile, isUploading } = useFileUpload(sessionId || '');

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  function buildContent(): string | ContentBlock[] {
    const trimmed = message.trim();

    if (!hasImages && !fileAttachments.length) {
      return trimmed;
    }

    const blocks: ContentBlock[] = [];

    if (trimmed) {
      const textBlock: TextContentBlock = { type: 'text', text: trimmed };
      blocks.push(textBlock);
    }

    // Add image blocks
    if (hasImages) {
      blocks.push(...images);
    }

    // Add file references as text blocks
    if (fileAttachments.length > 0) {
      const fileText = fileAttachments
        .map(f => `[File: ${f.file.name}]`)
        .join('\n');
      blocks.push({ type: 'text', text: fileText });
    }

    return blocks;
  }

  async function handleSubmit() {
    if (disabled || (!message.trim() && !hasImages && fileAttachments.length === 0)) {
      return;
    }

    // Upload files before sending
    if (fileAttachments.length > 0 && sessionId) {
      for (const attachment of fileAttachments) {
        try {
          await uploadFile({ file: attachment.file });
        } catch (error) {
          console.error('Failed to upload file:', error);
          toast.error(`Failed to upload ${attachment.file.name}`);
        }
      }
    }

    onSend(buildContent());
    setMessage('');
    clearImages();
    setFileAttachments([]);
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
    setAttachmentMenuOpen(false);
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (files && files.length > 0) {
      const newFiles = Array.from(files).map(file => ({
        id: `${Date.now()}-${Math.random()}`,
        file,
      }));
      setFileAttachments(prev => [...prev, ...newFiles]);
    }
    setAttachmentMenuOpen(false);
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

  function removeFileAttachment(id: string) {
    setFileAttachments(prev => prev.filter(f => f.id !== id));
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const audioChunks: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const audioFile = new File([audioBlob], `recording-${Date.now()}.webm`, { type: 'audio/webm' });

        // Add as file attachment
        setFileAttachments(prev => [...prev, {
          id: `audio-${Date.now()}`,
          file: audioFile,
        }]);

        setIsRecording(false);
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      toast.error('Could not access microphone');
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  }

  const hasContent = message.trim() || hasImages || fileAttachments.length > 0;
  const totalAttachments = images.length + fileAttachments.length;

  return (
    <div className="bg-background px-2 sm:px-4 py-2 sm:py-3">
      <div className="mx-auto max-w-3xl">
        {/* Single Container - Textarea + Buttons inside */}
        <div className="relative rounded-2xl border border-border/40 bg-background/95 backdrop-blur-sm shadow-sm overflow-hidden transition-shadow focus-within:border-border/60 focus-within:shadow-md">
          {/* Textarea - Full Width */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder="Message Claude..."
            rows={2}
            className="chat-textarea w-full min-h-[60px] max-h-[180px] resize-none bg-transparent px-3 sm:px-4 py-3 pr-28 text-sm placeholder:text-muted-foreground/60 disabled:cursor-not-allowed disabled:opacity-50 leading-relaxed"
            style={{ fieldSizing: 'content' }}
            disabled={disabled || isRecording}
          />

          {/* Buttons Row - Floating on right side */}
          <div className="absolute right-1.5 bottom-1.5 flex items-center gap-0.5 sm:gap-1">
            {/* Attachment Menu */}
            <Popover open={attachmentMenuOpen} onOpenChange={setAttachmentMenuOpen}>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={`h-8 w-8 sm:h-9 sm:w-9 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted-foreground/10 shrink-0 transition-all ${
                    attachmentMenuOpen ? 'bg-muted-foreground/15' : ''
                  }`}
                  disabled={disabled || isRecording}
                  title="Add attachment"
                >
                  <Plus className="h-4 w-4 sm:h-5 sm:w-5" />
                </Button>
              </PopoverTrigger>
              <PopoverContent side="top" align="end" className="w-44 p-1.5">
                <div className="space-y-0.5">
                  <label htmlFor="image-upload" className="flex items-center gap-2 px-2.5 py-2 rounded-md hover:bg-muted cursor-pointer transition-colors">
                    <ImageIcon className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Image</span>
                    <input
                      id="image-upload"
                      ref={fileInputRef}
                      type="file"
                      accept="image/png, image/jpeg, image/gif, image/webp"
                      multiple
                      className="hidden"
                      onChange={handleImageSelect}
                    />
                  </label>
                  <label htmlFor="file-upload" className="flex items-center gap-2 px-2.5 py-2 rounded-md hover:bg-muted cursor-pointer transition-colors">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">File</span>
                    <input
                      id="file-upload"
                      type="file"
                      multiple
                      className="hidden"
                      onChange={handleFileSelect}
                    />
                  </label>
                </div>
              </PopoverContent>
            </Popover>

            {/* Microphone Button */}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className={`h-8 w-8 sm:h-9 sm:w-9 rounded-lg shrink-0 transition-all ${
                isRecording
                  ? 'bg-destructive/10 text-destructive hover:bg-destructive/20 animate-pulse'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted-foreground/10'
              }`}
              disabled={disabled || isStreaming}
              onClick={isRecording ? stopRecording : startRecording}
              title={isRecording ? 'Stop recording' : 'Record audio'}
            >
              <Mic className="h-4 w-4 sm:h-5 sm:w-5" />
            </Button>

            {/* Send/Cancel Button */}
            {isStreaming ? (
              <Button
                onClick={onCancel}
                disabled={isCancelling}
                size="icon"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-lg bg-black hover:bg-black/90 text-white shadow-sm transition-colors dark:bg-white dark:hover:bg-white/90 dark:text-black"
              >
                {isCancelling ? <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" /> : <Square className="h-4 w-4 sm:h-5 sm:w-5" />}
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={!hasContent || disabled || isUploading || isRecording}
                size="icon"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-lg bg-primary hover:bg-primary/90 text-white shadow-sm transition-colors disabled:opacity-50"
              >
                {isUploading ? (
                  <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 sm:h-5 sm:w-5" />
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Attachments Preview */}
        {(hasImages || fileAttachments.length > 0) && (
          <div className="mt-2 flex gap-1.5 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">
            {images.map((image, index) => (
              <ImageAttachment
                key={`image-${index}`}
                image={image}
                index={index}
                onRemove={removeImage}
                disabled={disabled}
              />
            ))}
            {fileAttachments.map((attachment) => (
              <div
                key={attachment.id}
                className="relative group h-14 w-14 sm:h-16 sm:w-16 rounded-xl border border-border/60 overflow-hidden shrink-0 bg-muted/30 hover:bg-muted/50 transition-colors"
              >
                <div className="h-full w-full flex flex-col items-center justify-center p-1.5 text-center">
                  <FileText className="h-5 w-5 sm:h-6 sm:w-6 text-muted-foreground/70 mb-0.5" />
                  <p className="text-[9px] sm:text-[10px] text-muted-foreground/70 truncate w-full leading-tight">
                    {attachment.file.name}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => removeFileAttachment(attachment.id)}
                  className="absolute top-0.5 right-0.5 h-5 w-5 sm:h-6 sm:w-6 rounded-lg bg-destructive/90 text-white hover:bg-destructive flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 shadow-sm"
                  disabled={disabled}
                  title="Remove file"
                >
                  <X className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Recording Indicator */}
        {isRecording && (
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <div className="h-1.5 w-1.5 rounded-full bg-destructive animate-pulse" />
            <span className="font-medium">Recording...</span>
          </div>
        )}
      </div>
    </div>
  );
}
