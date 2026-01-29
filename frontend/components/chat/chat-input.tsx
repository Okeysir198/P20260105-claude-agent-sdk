'use client';
import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Square, Loader2, MoreVertical, Minimize2 } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ChatInputProps {
  onSend: (message: string) => void;
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

  const handleSubmit = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  return (
    <div className="bg-background px-2 sm:px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-background p-2 shadow-sm">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
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
                disabled={!message.trim() || disabled}
                size="icon"
                className="h-10 w-10 rounded-xl bg-primary text-white hover:bg-primary-hover disabled:opacity-50"
              >
                <Send className="h-5 w-5" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
