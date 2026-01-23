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

  return (
    <div className="my-4 overflow-hidden rounded-lg border bg-popover text-sm">
      {/* Header with language and copy button */}
      <div className="flex items-center justify-between border-b px-4 py-2 bg-muted/50">
        <span className="text-xs font-medium uppercase text-muted-foreground">
          {language || 'code'}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={handleCopy}
          title="Copy to clipboard"
        >
          {copied ? (
            <>
              <Check className="mr-1 h-3.5 w-3.5" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="mr-1 h-3.5 w-3.5" />
              Copy
            </>
          )}
        </Button>
      </div>

      {/* Code content with syntax highlighting */}
      <pre className="max-h-96 overflow-x-auto bg-popover p-4">
        <code className="font-mono text-xs leading-relaxed">{cleanCode}</code>
      </pre>
    </div>
  );
}
