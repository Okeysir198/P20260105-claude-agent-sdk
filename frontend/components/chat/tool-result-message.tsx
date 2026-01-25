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
  FileText
} from 'lucide-react';
import { toast } from 'sonner';

// Content type detection
type ContentType = 'code' | 'json' | 'error' | 'text';

function detectContentType(content: string): ContentType {
  if (!content) return 'text';

  // Check for JSON
  const trimmed = content.trim();
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      JSON.parse(trimmed);
      return 'json';
    } catch {
      // Not valid JSON, continue checking
    }
  }

  // Check for error patterns
  if (content.toLowerCase().includes('error:') ||
      content.toLowerCase().includes('exception') ||
      content.toLowerCase().includes('traceback') ||
      content.toLowerCase().includes('failed:') ||
      content.toLowerCase().includes('errno') ||
      content.match(/^(fatal|error|warning):/im)) {
    return 'error';
  }

  // Check for common code patterns
  if (content.includes('function ') ||
      content.includes('const ') ||
      content.includes('import ') ||
      content.includes('export ') ||
      content.includes('def ') ||
      content.includes('class ') ||
      content.includes('async ') ||
      content.includes('await ') ||
      content.includes('return ') ||
      content.match(/^(import|from|package|using|#include)/m)) {
    return 'code';
  }

  return 'text';
}

// Styling maps for different content types
const CONTENT_STYLES: Record<ContentType, string> = {
  code: 'bg-zinc-900 text-zinc-100 dark:bg-zinc-950',
  json: 'bg-[#1e1e1e] text-[#d4d4d4]',
  error: 'bg-red-950/30 text-red-200 border-l-2 border-red-500/50',
  text: 'bg-muted text-foreground',
};

const CONTENT_ICONS: Record<ContentType, React.ElementType> = {
  code: Code2,
  json: FileJson,
  error: AlertTriangle,
  text: FileText,
};

const CONTENT_LABELS: Record<ContentType, string> = {
  code: 'Code',
  json: 'JSON',
  error: 'Error',
  text: 'Output',
};

// Preview configuration
const PREVIEW_LINES = 5;
const MAX_LINE_LENGTH = 120;

// Helper to truncate long lines
function truncateLine(line: string, maxLength: number): string {
  if (line.length <= maxLength) return line;
  return line.slice(0, maxLength - 3) + '...';
}

// Format JSON with indentation
function formatJson(content: string): string {
  try {
    const parsed = JSON.parse(content.trim());
    return JSON.stringify(parsed, null, 2);
  } catch {
    return content;
  }
}

// Syntax highlight JSON
function highlightJson(json: string): React.ReactNode {
  // Simple JSON syntax highlighting
  const highlighted = json
    .replace(/"([^"]+)":/g, '<span class="text-[#9cdcfe]">"$1"</span>:') // keys
    .replace(/: "((?:[^"\\]|\\.)*)"/g, ': <span class="text-[#ce9178]">"$1"</span>') // string values
    .replace(/: (\d+\.?\d*)/g, ': <span class="text-[#b5cea8]">$1</span>') // numbers
    .replace(/: (true|false)/g, ': <span class="text-[#569cd6]">$1</span>') // booleans
    .replace(/: (null)/g, ': <span class="text-[#569cd6]">$1</span>'); // null

  return <span dangerouslySetInnerHTML={{ __html: highlighted }} />;
}

// Copy button sub-component
function CopyButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success('Copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      toast.error('Failed to copy to clipboard');
    }
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-6 w-6 p-0 hover:bg-muted/80"
      onClick={handleCopy}
      title="Copy to clipboard"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <Copy className="h-3.5 w-3.5 text-muted-foreground" />
      )}
    </Button>
  );
}

// Line numbers component
function LineNumbers({ count, startLine = 1 }: { count: number; startLine?: number }) {
  return (
    <div className="select-none pr-3 text-right text-[#6e7681] border-r border-[#3d3d3d] mr-3 min-w-[2.5rem]">
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

export function ToolResultMessage({ message, toolName }: ToolResultMessageProps) {
  const [expanded, setExpanded] = useState(false);
  const [showLineNumbers, setShowLineNumbers] = useState(false);

  const effectiveToolName = toolName || message.toolName;
  const contentType = message.isError ? 'error' : detectContentType(message.content);

  // Format content (especially JSON)
  const formattedContent = contentType === 'json'
    ? formatJson(message.content)
    : message.content;

  const lines = formattedContent.split('\n');
  const lineCount = lines.length;

  // Create preview with truncated lines
  const previewLines = lines.slice(0, PREVIEW_LINES).map(line => truncateLine(line, MAX_LINE_LENGTH));
  const preview = previewLines.join('\n');
  const hasMoreLines = lineCount > PREVIEW_LINES;

  // Get content type icon
  const ContentIcon = CONTENT_ICONS[contentType];

  return (
    <div className="group flex gap-3 py-1.5 px-4">
      {/* Status icon */}
      <div className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded",
        message.isError ? "bg-red-500/10" : "bg-muted"
      )}>
        {message.isError ? (
          <XCircle className="h-4 w-4 text-destructive" />
        ) : (
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-500" />
        )}
      </div>

      {/* Content area */}
      <div className="min-w-0 flex-1">
        <Card className={cn(
          "overflow-hidden rounded-md shadow-none max-w-2xl",
          message.isError && "border-red-500/30"
        )}>
          {/* Header */}
          <div className="flex items-center justify-between border-b px-3 py-1.5 bg-muted/50">
            <Button
              variant="ghost"
              size="sm"
              className="justify-start font-mono text-xs hover:bg-muted/50 p-0 h-auto"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <ChevronDown className="mr-2 h-4 w-4" />
              ) : (
                <ChevronRight className="mr-2 h-4 w-4" />
              )}
              <ContentIcon className="mr-2 h-3.5 w-3.5 text-muted-foreground" />
              <span>
                {message.isError ? 'Error Output' : effectiveToolName ? `${effectiveToolName} Output` : 'Tool Output'}
              </span>
              {message.isError && (
                <span className="ml-2 px-1.5 py-0.5 text-[10px] font-medium bg-red-500/20 text-red-400 rounded">
                  ERROR
                </span>
              )}
            </Button>

            <div className="flex items-center gap-2">
              {/* Content type badge */}
              <span className={cn(
                "text-[10px] font-medium px-1.5 py-0.5 rounded uppercase",
                contentType === 'error' ? "bg-red-500/20 text-red-400" :
                contentType === 'json' ? "bg-blue-500/20 text-blue-400" :
                contentType === 'code' ? "bg-purple-500/20 text-purple-400" :
                "bg-muted text-muted-foreground"
              )}>
                {CONTENT_LABELS[contentType]}
              </span>

              {/* Line count badge */}
              <span className="text-xs text-muted-foreground">
                {lineCount} {lineCount === 1 ? 'line' : 'lines'}
              </span>

              {/* Line numbers toggle (only for code/json) */}
              {expanded && (contentType === 'code' || contentType === 'json') && lineCount > 1 && (
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

              {/* Copy button */}
              <CopyButton content={formattedContent} />
            </div>
          </div>

          {/* Content */}
          <pre className={cn(
            "max-h-96 overflow-auto p-3 text-xs font-mono leading-relaxed",
            CONTENT_STYLES[contentType]
          )}>
            {expanded ? (
              <div className="flex">
                {showLineNumbers && (contentType === 'code' || contentType === 'json') && (
                  <LineNumbers count={lineCount} />
                )}
                <code className="flex-1 whitespace-pre-wrap break-words">
                  {contentType === 'json' ? highlightJson(formattedContent) : formattedContent}
                </code>
              </div>
            ) : (
              <>
                <code className="whitespace-pre-wrap break-words">
                  {contentType === 'json' ? highlightJson(preview) : preview}
                </code>
                {hasMoreLines && (
                  <span className="block mt-2 text-muted-foreground/70 italic text-[11px]">
                    ... {lineCount - PREVIEW_LINES} more {lineCount - PREVIEW_LINES === 1 ? 'line' : 'lines'}
                  </span>
                )}
              </>
            )}
          </pre>
        </Card>

        {/* Timestamp */}
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}
