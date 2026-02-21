'use client';

import { useState, useRef, useEffect, useCallback, createElement } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Square, Loader2, Plus, Mic, Image as ImageIcon, FileText, X, Trash2 } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useDropzone } from 'react-dropzone';
import type { ContentBlock, TextContentBlock, AudioContentBlock, FileContentBlock } from '@/types';
import { useImageUpload } from '@/hooks/use-image-upload';
import { ImageAttachment } from './image-attachment';
import { ChatDropOverlay } from './chat-drop-overlay';
import { InlineAudioPlayer } from './media/inline-audio-player';
import { useFileUpload } from '@/hooks/use-files';
import { useChatStore } from '@/lib/store/chat-store';
import { getFileIcon, getFileColorClasses, formatFileSize } from '@/lib/utils/file-utils';
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
  const [recordingTime, setRecordingTime] = useState(0);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
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

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      const imageFiles: File[] = [];
      const otherFiles: File[] = [];

      for (const file of acceptedFiles) {
        if (file.type.startsWith('image/')) {
          imageFiles.push(file);
        } else {
          otherFiles.push(file);
        }
      }

      if (imageFiles.length > 0) {
        addImages(imageFiles);
      }

      if (otherFiles.length > 0) {
        const newFiles = otherFiles.map(file => ({
          id: `${Date.now()}-${Math.random()}`,
          file,
        }));
        setFileAttachments(prev => [...prev, ...newFiles]);
      }
    },
    noClick: true,
    noKeyboard: true,
  });

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

    // Upload files before sending message
    if (fileAttachments.length > 0) {
      if (sessionId) {
        // Session exists — upload immediately
        for (const attachment of fileAttachments) {
          try {
            await uploadFile({ file: attachment.file });
          } catch (error) {
            console.error('Failed to upload file:', error);
            toast.error(`Failed to upload ${attachment.file.name}`);
          }
        }
      } else {
        // No session yet — store files as pending for upload after session creation
        useChatStore.getState().setPendingFiles(
          fileAttachments.map(a => ({ file: a.file, name: a.file.name }))
        );
      }
    }

    // Build media blocks for local UI display (blob URLs for audio/files)
    const mediaBlocks: ContentBlock[] = [];
    for (const attachment of fileAttachments) {
      const blobUrl = URL.createObjectURL(attachment.file);
      if (attachment.file.type.startsWith('audio/')) {
        mediaBlocks.push({
          type: 'audio',
          source: { url: blobUrl, mime_type: attachment.file.type },
          filename: attachment.file.name,
        } satisfies AudioContentBlock);
      } else {
        mediaBlocks.push({
          type: 'file',
          source: { url: blobUrl, mime_type: attachment.file.type },
          filename: attachment.file.name,
          size: attachment.file.size,
        } satisfies FileContentBlock);
      }
    }

    onSend(buildContent());

    // Enrich the last user message with media blocks for rich UI rendering
    if (mediaBlocks.length > 0) {
      useChatStore.getState().updateLastMessage((msg) => {
        const existingBlocks = typeof msg.content === 'string'
          ? [{ type: 'text' as const, text: msg.content }]
          : [...msg.content];
        return { ...msg, content: [...existingBlocks, ...mediaBlocks] };
      });
    }

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

  const stopRecordingTimer = useCallback(() => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  }, []);

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
        setIsRecording(false);
        stopRecordingTimer();
        setRecordingTime(0);
        stream.getTracks().forEach(track => track.stop());

        // If cancelled, don't save the recording
        if (cancelledRef.current) {
          cancelledRef.current = false;
          return;
        }

        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const audioFile = new File([audioBlob], `recording-${Date.now()}.webm`, { type: 'audio/webm' });

        setFileAttachments(prev => [...prev, {
          id: `audio-${Date.now()}`,
          file: audioFile,
          preview: URL.createObjectURL(audioBlob),
        }]);
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
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

  const cancelledRef = useRef(false);

  function cancelRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      cancelledRef.current = true;
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
  }

  // Cleanup timer on unmount
  useEffect(() => {
    return () => stopRecordingTimer();
  }, [stopRecordingTimer]);

  function formatRecordingTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  const hasContent = message.trim() || hasImages || fileAttachments.length > 0;

  return (
    <div className="bg-background px-2 sm:px-4 py-2 sm:py-3">
      <div className="mx-auto max-w-3xl">
        {/* Single Container - Textarea + Buttons inside */}
        <div {...getRootProps()} className="relative rounded-2xl border border-border/40 bg-background/95 backdrop-blur-sm shadow-sm overflow-hidden transition-shadow focus-within:border-border/60 focus-within:shadow-md">
          <input {...getInputProps()} />
          <ChatDropOverlay isDragActive={isDragActive} />

          {isRecording ? (
            /* Recording Bar — replaces textarea during recording */
            <div className="flex items-center gap-3 px-3 sm:px-4 py-3 min-h-[60px]">
              {/* Red pulse dot */}
              <div className="relative flex-shrink-0">
                <div className="h-3 w-3 rounded-full bg-destructive animate-pulse" />
                <div className="absolute inset-0 h-3 w-3 rounded-full bg-destructive/40 animate-ping" />
              </div>

              {/* Animated waveform bars */}
              <div className="flex items-center gap-[3px] h-8 flex-1">
                {Array.from({ length: 24 }).map((_, i) => (
                  <div
                    key={i}
                    className="flex-1 max-w-[4px] rounded-full bg-destructive/60"
                    style={{
                      animation: `waveform ${0.4 + (i % 5) * 0.1}s ease-in-out infinite alternate`,
                      animationDelay: `${i * 0.05}s`,
                    }}
                  />
                ))}
              </div>

              {/* Timer */}
              <span className="text-sm font-mono tabular-nums text-destructive font-medium min-w-[36px] text-right">
                {formatRecordingTime(recordingTime)}
              </span>

              {/* Cancel button */}
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 shrink-0 transition-colors"
                onClick={cancelRecording}
                title="Cancel recording"
              >
                <Trash2 className="h-4 w-4 sm:h-5 sm:w-5" />
              </Button>

              {/* Stop/Send button */}
              <Button
                type="button"
                size="icon"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-lg bg-destructive hover:bg-destructive/90 text-white shadow-sm transition-colors"
                onClick={stopRecording}
                title="Stop recording"
              >
                <Square className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              </Button>
            </div>
          ) : (
            /* Normal input mode */
            <>
              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                placeholder="Message Claude..."
                rows={2}
                className="chat-textarea w-full min-h-[60px] max-h-[180px] resize-none bg-transparent px-3 sm:px-4 py-3 pr-28 text-base sm:text-sm placeholder:text-muted-foreground/60 disabled:cursor-not-allowed disabled:opacity-50 leading-relaxed"
                style={{ fieldSizing: 'content' }}
                disabled={disabled}
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
                      disabled={disabled}
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
                  className="h-8 w-8 sm:h-9 sm:w-9 rounded-lg shrink-0 transition-all text-muted-foreground hover:text-foreground hover:bg-muted-foreground/10"
                  disabled={disabled || isStreaming}
                  onClick={startRecording}
                  title="Record audio"
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
                    disabled={!hasContent || disabled || isUploading}
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
            </>
          )}
        </div>

        {/* Attachments Preview */}
        {(hasImages || fileAttachments.length > 0) && (
          <div className="mt-2 flex flex-col gap-1.5">
            {/* Audio attachments — full-width inline player */}
            {fileAttachments
              .filter(a => a.file.type.startsWith('audio/'))
              .map((attachment) => {
                const blobUrl = attachment.preview || URL.createObjectURL(attachment.file);
                return (
                  <div
                    key={attachment.id}
                    className="group relative flex items-center gap-2 rounded-xl border border-border/40 bg-muted/30 px-3 py-2 transition-colors hover:bg-muted/50"
                  >
                    <div className="flex-1 min-w-0">
                      <InlineAudioPlayer
                        src={blobUrl}
                        filename={attachment.file.name}
                        mimeType={attachment.file.type}
                        compact
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => removeFileAttachment(attachment.id)}
                      className="flex-shrink-0 h-6 w-6 rounded-lg bg-destructive/80 text-white hover:bg-destructive flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 shadow-sm"
                      disabled={disabled}
                      title="Remove recording"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                );
              })}

            {/* Image + file attachments — horizontal scroll row */}
            {(hasImages || fileAttachments.some(a => !a.file.type.startsWith('audio/'))) && (
              <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">
                {images.map((image, index) => (
                  <ImageAttachment
                    key={`image-${index}`}
                    image={image}
                    index={index}
                    onRemove={removeImage}
                    disabled={disabled}
                  />
                ))}
                {fileAttachments
                  .filter(a => !a.file.type.startsWith('audio/'))
                  .map((attachment) => {
                    const FileIconComponent = getFileIcon(undefined, attachment.file.name);
                    const colorClasses = getFileColorClasses(attachment.file.type, attachment.file.name);

                    return (
                      <div
                        key={attachment.id}
                        className="relative group h-16 w-16 sm:h-[72px] sm:w-[72px] rounded-xl border border-border/60 overflow-hidden shrink-0 bg-muted/30 hover:bg-muted/50 transition-colors"
                      >
                        <div className="h-full w-full flex flex-col items-center justify-center p-1.5 text-center gap-0.5">
                          {createElement(FileIconComponent, { className: `h-5 w-5 sm:h-6 sm:w-6 shrink-0 ${colorClasses.iconColor}` })}
                          <p className="text-[11px] sm:text-[10px] text-muted-foreground/70 truncate w-full leading-tight">
                            {attachment.file.name}
                          </p>
                          <p className="text-[9px] sm:text-[10px] text-muted-foreground/50 leading-tight">
                            {formatFileSize(attachment.file.size)}
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
                    );
                  })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
