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
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border/50',
          isRunning && 'animate-pulse'
        )}
        style={{
          backgroundColor: `hsl(var(--muted) / 0.5)`,
          ...colorStyles.iconText
        }}
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ToolIcon className="h-3.5 w-3.5" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        {message.toolInput && (
          <Card
            className="overflow-hidden rounded-lg shadow-sm max-w-2xl bg-muted/30 border border-border/50"
          >
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start rounded-none border-b border-border/50 px-3 py-2 text-xs hover:bg-muted/50 h-auto min-h-[36px]"
              onClick={() => setExpanded(!expanded)}
            >
              <div className="flex items-center gap-2 w-full">
                {expanded ? (
                  <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                )}
                <span className="font-medium text-foreground">{toolName}</span>
                {!expanded && summary && (
                  <>
                    <span className="text-muted-foreground/60">:</span>
                    <span className="text-muted-foreground/80 font-mono text-[11px] truncate">
                      {summary}
                    </span>
                  </>
                )}
                {isRunning && (
                  <span className="ml-auto text-xs text-muted-foreground flex items-center gap-1.5">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-foreground/40 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-foreground/60"></span>
                    </span>
                    <span className="text-[11px]">Running</span>
                  </span>
                )}
              </div>
            </Button>
            {expanded && (
              <div className="p-3 bg-background/50">
                <ToolInputDisplay toolName={toolName} input={message.toolInput} />
              </div>
            )}
          </Card>
        )}
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[11px] text-muted-foreground">{formatTime(message.timestamp)}</span>
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
          <p className="text-[11px] text-muted-foreground italic">{description}</p>
        )}
        {command && (
          <pre
            className="p-2.5 rounded-md text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all bg-muted/50 border border-border/50"
            style={{
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
          <p className="text-[11px] text-muted-foreground">Timeout: {input.timeout}ms</p>
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
            <span className="text-[11px] text-muted-foreground">File:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
              style={colorStyles.badge}
            >
              {filePath}
            </code>
          </div>
        )}
        {(offset !== undefined || limit !== undefined) && (
          <div className="flex gap-4 text-[11px] text-muted-foreground">
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
            <span className="text-[11px] text-muted-foreground">File:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
              style={colorStyles.badge}
            >
              {filePath}
            </code>
          </div>
        )}
        {content && (
          <div>
            <span className="text-[11px] text-muted-foreground block mb-1">Content:</span>
            <pre className="bg-muted/40 border border-border/50 p-2 rounded text-xs font-mono max-h-32 overflow-auto whitespace-pre-wrap break-all">
              {content.length > 500 ? content.slice(0, 500) + '\n... (truncated)' : content}
            </pre>
          </div>
        )}
        {oldString && (
          <div>
            <span className="text-[11px] text-muted-foreground block mb-1">Replace:</span>
            <pre
              className="p-2 rounded text-xs font-mono max-h-24 overflow-auto whitespace-pre-wrap break-all border border-border/50"
              style={{
                backgroundColor: 'hsl(var(--destructive) / 0.08)',
                color: 'hsl(var(--destructive))',
              }}
            >
              {oldString.length > 200 ? oldString.slice(0, 200) + '\n... (truncated)' : oldString}
            </pre>
          </div>
        )}
        {newString && (
          <div>
            <span className="text-[11px] text-muted-foreground block mb-1">With:</span>
            <pre
              className="p-2 rounded text-xs font-mono max-h-24 overflow-auto whitespace-pre-wrap break-all bg-muted/40 border border-border/50"
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
            <span className="text-[11px] text-muted-foreground">Pattern:</span>
            <code
              className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
              style={colorStyles.badge}
            >
              {pattern}
            </code>
          </div>
        )}
        {path && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground">Path:</span>
            <code className="bg-muted/50 border border-border/50 px-2 py-0.5 rounded text-xs font-mono">{path}</code>
          </div>
        )}
        {glob && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground">Glob:</span>
            <code className="bg-muted/50 border border-border/50 px-2 py-0.5 rounded text-xs font-mono">{glob}</code>
          </div>
        )}
      </div>
    );
  }

  // AskUserQuestion tool - display questions and options in a readable format
  if (toolName === 'AskUserQuestion') {
    const questions = input.questions as Array<{
      question: string;
      header?: string;
      options?: Array<{
        label: string;
        description?: string;
      }>;
      multiSelect?: boolean;
    }> | undefined;

    if (!questions || questions.length === 0) {
      return (
        <div className="text-[11px] text-muted-foreground italic">
          No questions defined
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {questions.map((q, qIdx) => (
          <div key={qIdx} className="space-y-2">
            {q.header && (
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {q.header}
              </div>
            )}
            <div className="text-xs font-medium text-foreground">
              {q.question}
            </div>
            {q.options && q.options.length > 0 && (
              <div className="space-y-1.5 pl-2">
                {q.options.map((opt, oIdx) => (
                  <div
                    key={oIdx}
                    className="flex items-start gap-2 text-[11px]"
                  >
                    <span className="text-muted-foreground/60 select-none mt-0.5">
                      {String.fromCharCode(65 + oIdx)}.
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-foreground">
                        {opt.label}
                      </div>
                      {opt.description && (
                        <div className="text-[10px] text-muted-foreground mt-0.5 leading-snug">
                          {opt.description}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {q.multiSelect !== undefined && (
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted/50 border border-border/50">
                  {q.multiSelect ? 'Multiple selection' : 'Single selection'}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  // TodoWrite tool - display todos in a task list format
  if (toolName === 'TodoWrite') {
    const todos = input.todos as Array<{
      content: string;
      status?: string;
      activeForm?: string;
    }> | undefined;

    if (!todos || todos.length === 0) {
      return (
        <div className="text-[11px] text-muted-foreground italic">
          No todos defined
        </div>
      );
    }

    return (
      <div className="space-y-1.5">
        {todos.map((todo, idx) => {
          const isPending = !todo.status || todo.status === 'pending';
          return (
            <div
              key={idx}
              className="flex items-start gap-2 text-[11px] p-2 rounded bg-muted/20 border border-border/30"
            >
              <div className="flex items-center justify-center w-4 h-4 mt-0.5 shrink-0">
                {isPending ? (
                  <div className="w-3 h-3 rounded-full border-2 border-muted-foreground/40" />
                ) : (
                  <div className="w-3 h-3 rounded-full bg-green-500/80 flex items-center justify-center">
                    <svg className="w-2 h-2 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-foreground">
                  {todo.activeForm || todo.content}
                </div>
                {todo.activeForm && todo.activeForm !== todo.content && (
                  <div className="text-[10px] text-muted-foreground mt-0.5">
                    {todo.content}
                  </div>
                )}
              </div>
              {todo.status && (
                <span className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded shrink-0",
                  isPending
                    ? "bg-yellow-500/10 text-yellow-500 border border-yellow-500/20"
                    : "bg-green-500/10 text-green-500 border border-green-500/20"
                )}>
                  {todo.status}
                </span>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // Fallback to JSON display for other tools
  return (
    <pre className="bg-muted/40 border border-border/50 p-3 rounded text-xs font-mono overflow-auto max-h-64 whitespace-pre-wrap break-all">
      {JSON.stringify(input, null, 2)}
    </pre>
  );
}
