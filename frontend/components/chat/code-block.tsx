'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language = 'text' }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const announcementTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Ensure code is always a string and clean it
  const cleanCode = typeof code === 'string' ? code : String(code || '');

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (announcementTimeoutRef.current) {
        clearTimeout(announcementTimeoutRef.current);
      }
    };
  }, []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cleanCode);
      setCopied(true);
      setAnnouncement('Code copied to clipboard');

      // Clear announcement after screen reader has time to announce it
      announcementTimeoutRef.current = setTimeout(() => {
        setCopied(false);
        setAnnouncement('');
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      setAnnouncement('Failed to copy code to clipboard');
      announcementTimeoutRef.current = setTimeout(() => {
        setAnnouncement('');
      }, 2000);
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
    <div
      className="group my-4 overflow-hidden rounded-lg border border-border/40 shadow-sm"
      role="region"
      aria-label={`Code block in ${language || 'text'}`}
    >
      {/* Screen reader announcement for copy action */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {announcement}
      </div>

      {/* Header with language and copy button */}
      <div className="flex items-center justify-between px-4 py-2 bg-muted/40 border-b border-border/40">
        <span
          className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-2"
          aria-hidden="true"
        >
          <span className="w-2 h-2 rounded-full bg-current opacity-40"></span>
          {language || 'code'}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2.5 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-all"
          onClick={handleCopy}
          title="Copy code to clipboard"
          aria-label={copied ? 'Code copied to clipboard' : `Copy ${language || 'code'} code to clipboard`}
          aria-pressed={copied}
        >
          {copied ? (
            <>
              <Check className="mr-1.5 h-3 w-3 text-green-500" aria-hidden="true" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy className="mr-1.5 h-3 w-3" aria-hidden="true" />
              <span>Copy</span>
            </>
          )}
        </Button>
      </div>

      {/* Code content - dark background like VS Code */}
      <pre
        className="max-h-96 overflow-x-auto p-4 scrollbar-thin"
        style={{ backgroundColor: 'hsl(var(--code-bg))' }}
        tabIndex={0}
        aria-label={`${language || 'Code'} content, ${cleanCode.split('\n').length} lines`}
      >
        <code className="font-mono text-[13px] leading-relaxed whitespace-pre-wrap break-words" style={{ color: 'hsl(var(--code-fg))' }}>
          {cleanCode}
        </code>
      </pre>
    </div>
  );
}
