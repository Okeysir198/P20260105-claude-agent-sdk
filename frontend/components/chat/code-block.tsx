'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language = 'text' }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  // Ensure code is always a string and clean it
  const cleanCode = typeof code === 'string' ? code : String(code || '');

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cleanCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Don't render if code is empty
  if (!cleanCode || cleanCode.trim() === '') {
    return (
      <div className="my-4 p-4 border border-dashed border-border/50 rounded-lg text-center text-muted-foreground/60 text-xs">
        No code to display
      </div>
    );
  }

  return (
    <div className="group my-4 overflow-hidden rounded-lg border border-border/40 shadow-sm">
      {/* Header with language and copy button */}
      <div className="flex items-center justify-between px-4 py-2 bg-muted/40 border-b border-border/40">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-current opacity-40"></span>
          {language || 'code'}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2.5 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-all"
          onClick={handleCopy}
          title="Copy to clipboard"
        >
          {copied ? (
            <>
              <Check className="mr-1.5 h-3 w-3 text-green-500" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy className="mr-1.5 h-3 w-3" />
              <span>Copy</span>
            </>
          )}
        </Button>
      </div>

      {/* Code content - dark background like VS Code */}
      <pre className="max-h-96 overflow-x-auto p-4 scrollbar-thin" style={{ backgroundColor: 'hsl(var(--code-bg))' }}>
        <code className="font-mono text-[13px] leading-relaxed whitespace-pre-wrap break-words" style={{ color: 'hsl(var(--code-fg))' }}>
          {cleanCode}
        </code>
      </pre>
    </div>
  );
}
