'use client';

import { useState } from 'react';
import { Copy, Check, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import type { PreviewerProps } from './index';

export function TextPreviewer({ file, content }: PreviewerProps) {
  const [copied, setCopied] = useState(false);
  const text = content as string;
  const lineCount = text.split('\n').length;
  const charCount = text.length;

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Compact toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/40">
        <div className="flex items-center gap-2">
          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-[11px] text-muted-foreground hidden xs:inline">
            {lineCount.toLocaleString()} lines
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-7 px-2 gap-1.5 text-xs"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          <span className="hidden sm:inline">{copied ? 'Copied!' : 'Copy'}</span>
        </Button>
      </div>

      {/* Content with better typography */}
      <div className="flex-1 overflow-auto p-3 sm:p-4 bg-muted/20">
        <pre className="text-xs sm:text-sm font-mono whitespace-pre-wrap break-words leading-relaxed tabular-nums">
          {text}
        </pre>
      </div>
    </div>
  );
}

export default TextPreviewer;
