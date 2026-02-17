'use client';

import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import type { PreviewerProps } from './index';

export function TextPreviewer({ file, content }: PreviewerProps) {
  const [copied, setCopied] = useState(false);
  const text = content as string;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted">
        <span className="text-xs text-muted-foreground">{text.split('\n').length} lines</span>
        <button onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }} className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-accent text-xs">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4 bg-muted">
        <pre className="text-sm font-mono whitespace-pre-wrap">{text}</pre>
      </div>
    </div>
  );
}

export default TextPreviewer;
