'use client';
import type { ChatMessage } from '@/types';
import { formatTime, cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { getToolIcon, getToolColorStyles, getToolSummary } from '@/lib/tool-config';

interface ToolUseMessageProps {
  message: ChatMessage;
  isRunning?: boolean;
}

export function ToolUseMessage({ message, isRunning = false }: ToolUseMessageProps) {
  const [expanded, setExpanded] = useState(false);

  const toolName = message.toolName || '';
  const ToolIcon = getToolIcon(toolName);
  const colorStyles = getToolColorStyles(toolName);
  const summary = getToolSummary(toolName, message.toolInput);

  return (
    <div className="group flex gap-3 py-1.5 px-4">
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded',
          isRunning && 'animate-pulse'
        )}
        style={{ ...colorStyles.iconBg, ...colorStyles.iconText }}
      >
        {isRunning ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ToolIcon className="h-4 w-4" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        {message.toolInput && (
          <Card
            className="overflow-hidden rounded-md shadow-none max-w-2xl border-l-4"
            style={colorStyles.border}
          >
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
                <ToolInputDisplay toolName={toolName} input={message.toolInput} />
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

interface ToolInputDisplayProps {
  toolName: string;
  input: Record<string, unknown>;
}

/**
 * Renders tool-specific input display.
 */
function ToolInputDisplay({ toolName, input }: ToolInputDisplayProps) {
  const colorStyles = getToolColorStyles(toolName);

  if (toolName === 'Bash') {
    const command = input.command as string | undefined;
    const description = input.description as string | undefined;
    return (
      <div className="space-y-2">
        {description && (
          <p className="text-xs text-muted-foreground italic">{description}</p>
        )}
        {command && (
          <pre
            className="p-3 rounded text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all"
            style={{
              backgroundColor: 'hsl(var(--code-bg))',
              color: 'hsl(var(--code-fg))',
            }}
          >
            <span style={{ color: 'hsl(var(--code-prompt))' }} className="select-none">
              ${' '}
            </span>
            {command}
          </pre>
        )}
        {typeof input.timeout === 'number' && (
          <p className="text-xs text-muted-foreground">Timeout: {input.timeout}ms</p>
        )}
      </div>
    );
  }

  if (toolName === 'Read') {
    const filePath = input.file_path as string | undefined;
    const offset = input.offset as number | undefined;
    const limit = input.limit as number | undefined;
    return (
      <div className="space-y-2">
        {filePath && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">File:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono"
              style={colorStyles.badge}
            >
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

  if (toolName === 'Write' || toolName === 'Edit') {
    const filePath = input.file_path as string | undefined;
    const content = input.content as string | undefined;
    const oldString = input.old_string as string | undefined;
    const newString = input.new_string as string | undefined;
    return (
      <div className="space-y-2">
        {filePath && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">File:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono"
              style={colorStyles.badge}
            >
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
            <pre
              className="p-2 rounded text-xs font-mono max-h-24 overflow-auto whitespace-pre-wrap break-all"
              style={{
                backgroundColor: 'hsl(var(--destructive) / 0.1)',
                color: 'hsl(var(--destructive))',
              }}
            >
              {oldString.length > 200 ? oldString.slice(0, 200) + '\n... (truncated)' : oldString}
            </pre>
          </div>
        )}
        {newString && (
          <div>
            <span className="text-xs text-muted-foreground block mb-1">With:</span>
            <pre
              className="p-2 rounded text-xs font-mono max-h-24 overflow-auto whitespace-pre-wrap break-all"
              style={colorStyles.badge}
            >
              {newString.length > 200 ? newString.slice(0, 200) + '\n... (truncated)' : newString}
            </pre>
          </div>
        )}
      </div>
    );
  }

  if (toolName === 'Grep' || toolName === 'Glob') {
    const pattern = input.pattern as string | undefined;
    const path = input.path as string | undefined;
    const glob = input.glob as string | undefined;
    return (
      <div className="space-y-2">
        {pattern && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">Pattern:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono"
              style={colorStyles.badge}
            >
              {pattern}
            </code>
          </div>
        )}
        {path && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Path:</span>
            <code className="bg-muted px-2 py-0.5 rounded text-xs font-mono">{path}</code>
          </div>
        )}
        {glob && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Glob:</span>
            <code className="bg-muted px-2 py-0.5 rounded text-xs font-mono">{glob}</code>
          </div>
        )}
      </div>
    );
  }

  // Fallback to JSON display for other tools
  return (
    <pre className="bg-muted p-3 rounded text-xs font-mono overflow-auto max-h-64 whitespace-pre-wrap break-all">
      {JSON.stringify(input, null, 2)}
    </pre>
  );
}
