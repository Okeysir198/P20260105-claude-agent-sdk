'use client';

import { useState } from 'react';
import type { ChatMessage } from '@/types';
import { formatTime, cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  AlertTriangle,
  Code2,
  FileJson,
  FileText,
} from 'lucide-react';
import { toast } from 'sonner';

type ContentType = 'code' | 'json' | 'error' | 'text';

function detectContentType(content: string): ContentType {
  if (!content) return 'text';

  const trimmed = content.trim();

  // Check for JSON
  if (
    (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
    (trimmed.startsWith('[') && trimmed.endsWith(']'))
  ) {
    try {
      JSON.parse(trimmed);
      return 'json';
    } catch {
      // Not valid JSON, continue checking
    }
  }

  // Check for error patterns
  const errorPatterns = [
    'error:',
    'exception',
    'traceback',
    'failed:',
    'errno',
  ];
  const lowerContent = content.toLowerCase();
  const hasErrorPattern =
    errorPatterns.some((pattern) => lowerContent.includes(pattern)) ||
    content.match(/^(fatal|error|warning):/im);

  if (hasErrorPattern) {
    return 'error';
  }

  // Check for common code patterns
  const codePatterns = [
    'function ',
    'const ',
    'import ',
    'export ',
    'def ',
    'class ',
    'async ',
    'await ',
    'return ',
  ];
  const hasCodePattern =
    codePatterns.some((pattern) => content.includes(pattern)) ||
    content.match(/^(import|from|package|using|#include)/m);

  if (hasCodePattern) {
    return 'code';
  }

  return 'text';
}

const CONTENT_TYPE_CONFIG: Record<
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

const PREVIEW_LINES = 5;
const MAX_LINE_LENGTH = 120;

function truncateLine(line: string, maxLength: number): string {
  if (line.length <= maxLength) return line;
  return line.slice(0, maxLength - 3) + '...';
}

function formatJson(content: string): string {
  try {
    const parsed = JSON.parse(content.trim());
    return JSON.stringify(parsed, null, 2);
  } catch {
    return content;
  }
}

/**
 * Simple JSON syntax highlighting using CSS variables.
 */
function highlightJson(json: string): React.ReactNode {
  const highlighted = json
    .replace(
      /"([^"]+)":/g,
      '<span style="color: hsl(var(--json-key))">"$1"</span>:'
    )
    .replace(
      /: "((?:[^"\\]|\\.)*)"/g,
      ': <span style="color: hsl(var(--json-string))">"$1"</span>'
    )
    .replace(
      /: (\d+\.?\d*)/g,
      ': <span style="color: hsl(var(--json-number))">$1</span>'
    )
    .replace(
      /: (true|false)/g,
      ': <span style="color: hsl(var(--json-keyword))">$1</span>'
    )
    .replace(
      /: (null)/g,
      ': <span style="color: hsl(var(--json-keyword))">$1</span>'
    );

  return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
}

function CopyButton({ content }: { content: string }): React.ReactNode {
  const [copied, setCopied] = useState(false);

  async function handleCopy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success('Copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      toast.error('Failed to copy to clipboard');
    }
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-6 w-6 p-0 hover:bg-muted/80"
      onClick={handleCopy}
      title="Copy to clipboard"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5" style={{ color: 'hsl(var(--progress-high))' }} />
      ) : (
        <Copy className="h-3.5 w-3.5 text-muted-foreground" />
      )}
    </Button>
  );
}

function LineNumbers({
  count,
  startLine = 1,
}: {
  count: number;
  startLine?: number;
}): React.ReactNode {
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
}

interface ToolResultMessageProps {
  message: ChatMessage;
  toolName?: string;
}

export function ToolResultMessage({
  message,
  toolName,
}: ToolResultMessageProps): React.ReactNode {
  const [expanded, setExpanded] = useState(false);
  const [showLineNumbers, setShowLineNumbers] = useState(false);

  const effectiveToolName = toolName || message.toolName;
  const contentType = message.isError ? 'error' : detectContentType(message.content);
  const config = CONTENT_TYPE_CONFIG[contentType];
  const ContentIcon = config.icon;

  const formattedContent =
    contentType === 'json' ? formatJson(message.content) : message.content;

  const lines = formattedContent.split('\n');
  const lineCount = lines.length;

  const previewLines = lines
    .slice(0, PREVIEW_LINES)
    .map((line) => truncateLine(line, MAX_LINE_LENGTH));
  const preview = previewLines.join('\n');
  const hasMoreLines = lineCount > PREVIEW_LINES;

  const contentStyle: React.CSSProperties = {
    backgroundColor: `hsl(var(${config.bgVar}))`,
    color: `hsl(var(${config.fgVar}))`,
  };

  if (contentType === 'error') {
    contentStyle.borderLeft = '2px solid hsl(var(--error-border) / 0.5)';
  }

  function getBadgeStyle(): React.CSSProperties {
    if (config.badgeBgVar && config.badgeFgVar) {
      return {
        backgroundColor: `hsl(var(${config.badgeBgVar}) / 0.2)`,
        color: `hsl(var(${config.badgeFgVar}))`,
      };
    }
    return {};
  }

  return (
    <div className="group flex gap-3 py-1.5 px-4">
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border"
        style={{ color: message.isError ? 'hsl(var(--destructive))' : 'hsl(var(--progress-high))' }}
      >
        {message.isError ? (
          <XCircle className="h-3.5 w-3.5" />
        ) : (
          <CheckCircle2 className="h-3.5 w-3.5" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <Card
          className={cn(
            'overflow-hidden rounded-lg shadow-sm max-w-2xl bg-muted/30 border-l-2',
            message.isError ? 'border-l-destructive' : ''
          )}
          style={message.isError ? {} : { borderLeftColor: 'hsl(var(--progress-high))' }}
        >
          <div className="flex items-center justify-between border-b border-border/50 px-3 py-1.5">
            <Button
              variant="ghost"
              size="sm"
              className="justify-start font-mono text-[11px] hover:bg-muted/50 p-0 h-auto"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <ChevronDown className="mr-2 h-3.5 w-3.5 text-muted-foreground" />
              ) : (
                <ChevronRight className="mr-2 h-3.5 w-3.5 text-muted-foreground" />
              )}
              <ContentIcon className="mr-2 h-3 w-3 text-muted-foreground" />
              <span className="text-foreground">
                {message.isError
                  ? 'Error Output'
                  : effectiveToolName
                    ? `${effectiveToolName} Output`
                    : 'Tool Output'}
              </span>
              {message.isError && (
                <span
                  className="ml-2 px-1.5 py-0.5 text-[10px] font-medium rounded"
                  style={getBadgeStyle()}
                >
                  ERROR
                </span>
              )}
            </Button>

            <div className="flex items-center gap-1.5">
              <span
                className="text-[10px] font-medium px-1.5 py-0.5 rounded uppercase"
                style={getBadgeStyle()}
              >
                {config.label}
              </span>

              <span className="text-[11px] text-muted-foreground">
                {lineCount} {lineCount === 1 ? 'line' : 'lines'}
              </span>

              {expanded &&
                (contentType === 'code' || contentType === 'json') &&
                lineCount > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-[10px] text-muted-foreground hover:text-foreground"
                    onClick={() => setShowLineNumbers(!showLineNumbers)}
                    title="Toggle line numbers"
                  >
                    #
                  </Button>
                )}

              <CopyButton content={formattedContent} />
            </div>
          </div>

          <pre
            className="max-h-96 overflow-auto p-3 text-xs font-mono leading-relaxed bg-background/30"
            style={contentStyle}
          >
            {expanded ? (
              <div className="flex">
                {showLineNumbers &&
                  (contentType === 'code' || contentType === 'json') && (
                    <LineNumbers count={lineCount} />
                  )}
                <code className="flex-1 whitespace-pre-wrap break-words">
                  {contentType === 'json'
                    ? highlightJson(formattedContent)
                    : formattedContent}
                </code>
              </div>
            ) : (
              <>
                <code className="whitespace-pre-wrap break-words">
                  {contentType === 'json' ? highlightJson(preview) : preview}
                </code>
                {hasMoreLines && (
                  <span className="block mt-2 text-muted-foreground/70 italic text-[11px]">
                    ... {lineCount - PREVIEW_LINES} more{' '}
                    {lineCount - PREVIEW_LINES === 1 ? 'line' : 'lines'}
                  </span>
                )}
              </>
            )}
          </pre>
        </Card>

        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
}
