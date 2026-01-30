'use client';

import { useState, memo } from 'react';
import { Button } from '@/components/ui/button';
import { Check, Copy, Code2, FileJson, FileText, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import type { ContentType } from '@/lib/tool-output-parser';

/**
 * Content type display configuration.
 */
export const CONTENT_TYPE_CONFIG: Record<
  ContentType,
  {
    icon: typeof Code2;
    label: string;
    bgVar: string;
    fgVar: string;
    badgeBgVar?: string;
    badgeFgVar?: string;
  }
> = {
  code: {
    icon: Code2,
    label: 'Code',
    bgVar: '--code-bg',
    fgVar: '--code-fg',
    badgeBgVar: '--badge-code-bg',
    badgeFgVar: '--badge-code-fg',
  },
  json: {
    icon: FileJson,
    label: 'JSON',
    bgVar: '--json-bg',
    fgVar: '--json-fg',
    badgeBgVar: '--badge-json-bg',
    badgeFgVar: '--badge-json-fg',
  },
  error: {
    icon: AlertTriangle,
    label: 'Error',
    bgVar: '--error-bg',
    fgVar: '--error-fg',
    badgeBgVar: '--badge-error-bg',
    badgeFgVar: '--badge-error-fg',
  },
  text: {
    icon: FileText,
    label: 'Output',
    bgVar: '--muted',
    fgVar: '--foreground',
  },
};

/**
 * Display constants for collapsed/expanded views.
 */
export const COLLAPSED_PREVIEW_LINES = 5;
export const EXPANDED_INITIAL_LINES = 20;
export const MAX_LINE_LENGTH = 120;

/**
 * Truncate a line to a maximum length.
 */
export function truncateLine(line: string, maxLength: number): string {
  if (line.length <= maxLength) return line;
  return line.slice(0, maxLength - 3) + '...';
}

/**
 * Copy button component for tool output.
 */
export const CopyButton = memo(function CopyButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success('Copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy to clipboard');
    }
  }

  return (
    <>
      <span role="status" aria-live="polite" className="sr-only">
        {copied ? 'Output copied to clipboard' : ''}
      </span>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 hover:bg-muted/80"
        onClick={handleCopy}
        title="Copy output to clipboard"
        aria-label={copied ? 'Output copied' : 'Copy output'}
        aria-pressed={copied}
      >
        {copied ? (
          <Check className="h-3.5 w-3.5" style={{ color: 'hsl(var(--progress-high))' }} aria-hidden="true" />
        ) : (
          <Copy className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
        )}
      </Button>
    </>
  );
});

/**
 * Line numbers component for code display.
 */
export const LineNumbers = memo(function LineNumbers({
  count,
  startLine = 1,
}: {
  count: number;
  startLine?: number;
}) {
  return (
    <div
      className="select-none pr-3 text-right mr-3 min-w-[2.5rem]"
      style={{
        color: 'hsl(var(--json-line-number))',
        borderRight: '1px solid hsl(var(--json-border))',
      }}
    >
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="leading-relaxed">
          {startLine + i}
        </div>
      ))}
    </div>
  );
});
