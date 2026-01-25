'use client';
import type { ChatMessage } from '@/types';
import { formatTime, cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Terminal,
  FileText,
  FileEdit,
  Search,
  Globe,
  FolderTree,
  MessageSquare,
  Wrench,
  ChevronDown,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { useState } from 'react';

// Tool-specific icons mapping
const TOOL_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  'Bash': Terminal,
  'Read': FileText,
  'Write': FileEdit,
  'Edit': FileEdit,
  'Grep': Search,
  'Glob': Search,
  'WebFetch': Globe,
  'WebSearch': Globe,
  'Task': FolderTree,
  'AskUserQuestion': MessageSquare,
};

// Tool-specific color classes
const TOOL_COLORS: Record<string, string> = {
  'Bash': 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  'Read': 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  'Write': 'bg-green-500/10 text-green-600 dark:text-green-400',
  'Edit': 'bg-green-500/10 text-green-600 dark:text-green-400',
  'Grep': 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
  'Glob': 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
  'WebFetch': 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
  'WebSearch': 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
  'Task': 'bg-orange-500/10 text-orange-600 dark:text-orange-400',
  'AskUserQuestion': 'bg-pink-500/10 text-pink-600 dark:text-pink-400',
};

// Tool-specific border colors for the card
const TOOL_BORDER_COLORS: Record<string, string> = {
  'Bash': 'border-l-amber-500',
  'Read': 'border-l-blue-500',
  'Write': 'border-l-green-500',
  'Edit': 'border-l-green-500',
  'Grep': 'border-l-purple-500',
  'Glob': 'border-l-purple-500',
  'WebFetch': 'border-l-cyan-500',
  'WebSearch': 'border-l-cyan-500',
  'Task': 'border-l-orange-500',
  'AskUserQuestion': 'border-l-pink-500',
};

/**
 * Generate a smart summary based on tool type and input
 */
function getToolSummary(toolName?: string, input?: Record<string, unknown>): string {
  if (!toolName || !input) return '';

  switch (toolName) {
    case 'Bash': {
      const command = input.command as string | undefined;
      if (command) {
        // Truncate long commands but try to keep meaningful parts
        const cleaned = command.replace(/\s+/g, ' ').trim();
        return cleaned.length > 60 ? cleaned.slice(0, 57) + '...' : cleaned;
      }
      return '';
    }
    case 'Read': {
      const filePath = input.file_path as string | undefined;
      if (filePath) {
        // Show just the filename for cleaner display
        const parts = filePath.split('/');
        return parts[parts.length - 1] || filePath;
      }
      return '';
    }
    case 'Write':
    case 'Edit': {
      const filePath = input.file_path as string | undefined;
      if (filePath) {
        const parts = filePath.split('/');
        return parts[parts.length - 1] || filePath;
      }
      return '';
    }
    case 'Grep': {
      const pattern = input.pattern as string | undefined;
      const path = input.path as string | undefined;
      if (pattern) {
        const truncatedPattern = pattern.length > 30 ? pattern.slice(0, 27) + '...' : pattern;
        return `"${truncatedPattern}"${path ? ` in ${path}` : ''}`;
      }
      return '';
    }
    case 'Glob': {
      const pattern = input.pattern as string | undefined;
      return pattern || '';
    }
    case 'WebFetch':
    case 'WebSearch': {
      const url = input.url as string | undefined;
      const query = input.query as string | undefined;
      if (url) {
        try {
          const urlObj = new URL(url);
          return urlObj.hostname;
        } catch {
          return url.slice(0, 40);
        }
      }
      if (query) {
        return query.length > 40 ? query.slice(0, 37) + '...' : query;
      }
      return '';
    }
    case 'Task': {
      const description = input.description as string | undefined;
      if (description) {
        return description.length > 50 ? description.slice(0, 47) + '...' : description;
      }
      return '';
    }
    case 'AskUserQuestion': {
      const question = input.question as string | undefined;
      if (question) {
        return question.length > 50 ? question.slice(0, 47) + '...' : question;
      }
      return '';
    }
    default:
      return '';
  }
}

/**
 * Render tool-specific input display
 */
function renderToolInput(toolName?: string, input?: Record<string, unknown>): React.ReactNode {
  if (!toolName || !input) return null;

  switch (toolName) {
    case 'Bash': {
      const command = input.command as string | undefined;
      const description = input.description as string | undefined;
      return (
        <div className="space-y-2">
          {description && (
            <p className="text-xs text-muted-foreground italic">{description}</p>
          )}
          {command && (
            <pre className="bg-zinc-900 text-zinc-100 dark:bg-zinc-950 p-3 rounded text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all">
              <span className="text-amber-400 select-none">$ </span>
              {command}
            </pre>
          )}
          {typeof input.timeout === 'number' && (
            <p className="text-xs text-muted-foreground">Timeout: {input.timeout}ms</p>
          )}
        </div>
      );
    }
    case 'Read': {
      const filePath = input.file_path as string | undefined;
      const offset = input.offset as number | undefined;
      const limit = input.limit as number | undefined;
      return (
        <div className="space-y-2">
          {filePath && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">File:</span>
              <code className="bg-blue-500/10 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded text-xs font-mono">
                {filePath}
              </code>
            </div>
          )}
          {(offset !== undefined || limit !== undefined) && (
            <div className="flex gap-4 text-xs text-muted-foreground">
              {offset !== undefined && <span>Offset: {offset}</span>}
              {limit !== undefined && <span>Limit: {limit}</span>}
            </div>
          )}
        </div>
      );
    }
    case 'Write':
    case 'Edit': {
      const filePath = input.file_path as string | undefined;
      const content = input.content as string | undefined;
      const oldString = input.old_string as string | undefined;
      const newString = input.new_string as string | undefined;
      return (
        <div className="space-y-2">
          {filePath && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">File:</span>
              <code className="bg-green-500/10 text-green-600 dark:text-green-400 px-2 py-0.5 rounded text-xs font-mono">
                {filePath}
              </code>
            </div>
          )}
          {content && (
            <div>
              <span className="text-xs text-muted-foreground block mb-1">Content:</span>
              <pre className="bg-muted p-2 rounded text-xs font-mono max-h-32 overflow-auto whitespace-pre-wrap break-all">
                {content.length > 500 ? content.slice(0, 500) + '\n... (truncated)' : content}
              </pre>
            </div>
          )}
          {oldString && (
            <div>
              <span className="text-xs text-muted-foreground block mb-1">Replace:</span>
              <pre className="bg-red-500/10 text-red-600 dark:text-red-400 p-2 rounded text-xs font-mono max-h-24 overflow-auto whitespace-pre-wrap break-all">
                {oldString.length > 200 ? oldString.slice(0, 200) + '\n... (truncated)' : oldString}
              </pre>
            </div>
          )}
          {newString && (
            <div>
              <span className="text-xs text-muted-foreground block mb-1">With:</span>
              <pre className="bg-green-500/10 text-green-600 dark:text-green-400 p-2 rounded text-xs font-mono max-h-24 overflow-auto whitespace-pre-wrap break-all">
                {newString.length > 200 ? newString.slice(0, 200) + '\n... (truncated)' : newString}
              </pre>
            </div>
          )}
        </div>
      );
    }
    case 'Grep':
    case 'Glob': {
      const pattern = input.pattern as string | undefined;
      const path = input.path as string | undefined;
      const glob = input.glob as string | undefined;
      return (
        <div className="space-y-2">
          {pattern && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-muted-foreground">Pattern:</span>
              <code className="bg-purple-500/10 text-purple-600 dark:text-purple-400 px-2 py-0.5 rounded text-xs font-mono">
                {pattern}
              </code>
            </div>
          )}
          {path && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Path:</span>
              <code className="bg-muted px-2 py-0.5 rounded text-xs font-mono">
                {path}
              </code>
            </div>
          )}
          {glob && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Glob:</span>
              <code className="bg-muted px-2 py-0.5 rounded text-xs font-mono">
                {glob}
              </code>
            </div>
          )}
        </div>
      );
    }
    default:
      // Fallback to JSON display for other tools
      return (
        <pre className="bg-muted p-3 rounded text-xs font-mono overflow-auto max-h-64 whitespace-pre-wrap break-all">
          {JSON.stringify(input, null, 2)}
        </pre>
      );
  }
}

interface ToolUseMessageProps {
  message: ChatMessage;
  isRunning?: boolean;
}

export function ToolUseMessage({ message, isRunning = false }: ToolUseMessageProps) {
  const [expanded, setExpanded] = useState(false);

  const toolName = message.toolName || '';
  const ToolIcon = TOOL_ICONS[toolName] || Wrench;
  const colorClass = TOOL_COLORS[toolName] || 'bg-primary/10 text-primary';
  const borderColor = TOOL_BORDER_COLORS[toolName] || 'border-l-primary';
  const summary = getToolSummary(toolName, message.toolInput);

  return (
    <div className="group flex gap-3 py-1.5 px-4">
      <div className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded",
        colorClass,
        isRunning && "animate-pulse"
      )}>
        {isRunning ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ToolIcon className="h-4 w-4" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        {message.toolInput && (
          <Card className={cn(
            "overflow-hidden rounded-md shadow-none max-w-2xl border-l-4",
            borderColor
          )}>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start rounded-none border-b px-4 py-2 text-xs hover:bg-muted/50 h-auto min-h-[40px]"
              onClick={() => setExpanded(!expanded)}
            >
              <div className="flex items-center gap-2 w-full">
                {expanded ? (
                  <ChevronDown className="h-4 w-4 shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 shrink-0" />
                )}
                <span className="font-semibold">{toolName}</span>
                {!expanded && summary && (
                  <>
                    <span className="text-muted-foreground">:</span>
                    <span className="text-muted-foreground font-mono truncate">
                      {summary}
                    </span>
                  </>
                )}
                {isRunning && (
                  <span className="ml-auto text-xs text-muted-foreground flex items-center gap-1">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-current"></span>
                    </span>
                    Running
                  </span>
                )}
              </div>
            </Button>
            {expanded && (
              <div className="p-4">
                {renderToolInput(toolName, message.toolInput)}
              </div>
            )}
          </Card>
        )}
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}
