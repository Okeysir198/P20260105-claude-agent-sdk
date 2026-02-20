'use client';

import { cn } from '@/lib/utils';
import { getToolColorStyles } from '@/lib/tool-config';
import { InlineDiff } from './diff-view';

import { Plus, RefreshCw, ListTodo, FileSearch2 } from 'lucide-react';

interface ToolInputDisplayProps {
  toolName: string;
  input: Record<string, unknown>;
  expanded?: boolean;
}

// Reusable field row component for label + badge pattern
interface FieldRowProps {
  label: string;
  value: string;
  colorStyles?: ReturnType<typeof getToolColorStyles>;
  additionalContent?: React.ReactNode;
}

function FieldRow({ label, value, colorStyles, additionalContent }: FieldRowProps) {
  return (
    <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
      <span className="text-xs sm:text-[11px] text-muted-foreground">{label}:</span>
      <code
        className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
        style={colorStyles?.badge}
      >
        {value}
      </code>
      {additionalContent}
    </div>
  );
}

type ToolRendererProps = {
  input: Record<string, unknown>;
  colorStyles?: ReturnType<typeof getToolColorStyles>;
};

const TOOL_RENDERERS: Record<string, React.FC<ToolRendererProps>> = {
  Bash: BashInputDisplay,
  Read: ReadInputDisplay,
  Write: WriteEditInputDisplay,
  Edit: WriteEditInputDisplay,
  Grep: SearchInputDisplay,
  Glob: SearchInputDisplay,
  Task: TaskInputDisplay,
  WebFetch: WebFetchInputDisplay,
  WebSearch: WebSearchInputDisplay,
  AskUserQuestion: AskUserQuestionInputDisplay,
  TodoWrite: TodoWriteInputDisplay,
  TaskCreate: TaskCreateInputDisplay,
  TaskUpdate: TaskUpdateInputDisplay,
  TaskList: TaskListInputDisplay,
  TaskGet: TaskGetInputDisplay,
};

/**
 * Renders tool-specific input display with appropriate formatting.
 */
export function ToolInputDisplay({ toolName, input }: ToolInputDisplayProps) {
  const colorStyles = getToolColorStyles(toolName);
  const Renderer = TOOL_RENDERERS[toolName];

  if (Renderer) {
    return <Renderer input={input} colorStyles={colorStyles} />;
  }

  return <JsonInputDisplay input={input} />;
}

// --- Tool-specific input displays ---

function BashInputDisplay({ input }: { input: Record<string, unknown> }) {
  const command = input.command as string | undefined;
  const description = input.description as string | undefined;

  return (
    <div className="space-y-2">
      {description && (
        <p className="text-xs sm:text-[11px] text-muted-foreground italic">{description}</p>
      )}
      {command && (
        <pre
          className="p-2.5 rounded-md text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all bg-muted/50 border border-border/50"
          style={{ color: 'hsl(var(--code-fg))' }}
        >
          <span style={{ color: 'hsl(var(--code-prompt))' }} className="select-none">
            ${' '}
          </span>
          {command}
        </pre>
      )}
      {typeof input.timeout === 'number' && (
        <p className="text-xs sm:text-[11px] text-muted-foreground">Timeout: {input.timeout}ms</p>
      )}
    </div>
  );
}

function ReadInputDisplay({ input, colorStyles }: ToolRendererProps) {
  const filePath = input.file_path as string | undefined;
  const offset = input.offset as number | undefined;
  const limit = input.limit as number | undefined;

  return (
    <div className="space-y-2">
      {filePath && <FieldRow label="File" value={filePath} colorStyles={colorStyles} />}
      {(offset !== undefined || limit !== undefined) && (
        <div className="flex gap-4 text-xs sm:text-[11px] text-muted-foreground">
          {offset !== undefined && <span>Offset: {offset}</span>}
          {limit !== undefined && <span>Limit: {limit}</span>}
        </div>
      )}
    </div>
  );
}

function WriteEditInputDisplay({ input, colorStyles }: ToolRendererProps) {
  const filePath = input.file_path as string | undefined;
  const content = input.content as string | undefined;
  const oldString = input.old_string as string | undefined;
  const newString = input.new_string as string | undefined;
  const replaceAll = input.replace_all as boolean | undefined;

  // Determine if this is an Edit operation (has old_string and newString)
  const isEditOperation = oldString !== undefined && newString !== undefined;

  return (
    <div className="space-y-2">
      {filePath && (
        <FieldRow
          label="File"
          value={filePath}
          colorStyles={colorStyles}
          additionalContent={
            replaceAll ? (
              <span className="text-xs sm:text-[10px] px-1.5 py-0.5 rounded bg-status-warning-bg text-status-warning-fg border border-status-warning/20">
                replace all
              </span>
            ) : undefined
          }
        />
      )}

      {/* Write operation - show content */}
      {content && !isEditOperation && (
        <div>
          <span className="text-xs sm:text-[11px] text-muted-foreground block mb-1">Content:</span>
          <pre className="bg-muted/40 border border-border/50 p-1.5 sm:p-2 rounded text-xs font-mono max-h-24 sm:max-h-32 overflow-auto whitespace-pre-wrap break-all">
            {content.length > 500 ? content.slice(0, 500) + '\n... (truncated)' : content}
          </pre>
        </div>
      )}

      {/* Edit operation - show diff view */}
      {isEditOperation && (
        <div>
          <span className="text-xs sm:text-[11px] text-muted-foreground block mb-1">Changes:</span>
          {/* Use InlineDiff for shorter content, DiffView for longer */}
          {(oldString.length + newString.length) < 300 ? (
            <InlineDiff oldContent={oldString} newContent={newString} />
          ) : (
            <div className="border rounded-md border-border/50 overflow-hidden">
              {filePath && (
                <div className="bg-muted/50 px-2 sm:px-3 py-1.5 border-b border-border/50 text-xs sm:text-[11px] text-muted-foreground">
                  {filePath}
                </div>
              )}
              <div className="p-2">
                <InlineDiff oldContent={oldString} newContent={newString} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SearchInputDisplay({ input, colorStyles }: ToolRendererProps) {
  const pattern = input.pattern as string | undefined;
  const path = input.path as string | undefined;
  const glob = input.glob as string | undefined;

  return (
    <div className="space-y-2">
      {pattern && <FieldRow label="Pattern" value={pattern} colorStyles={colorStyles} />}
      {path && (
        <div className="flex items-center gap-1.5 sm:gap-2">
          <span className="text-xs sm:text-[11px] text-muted-foreground">Path:</span>
          <code className="bg-muted/50 border border-border/50 px-2 py-0.5 rounded text-xs font-mono">
            {path}
          </code>
        </div>
      )}
      {glob && (
        <div className="flex items-center gap-1.5 sm:gap-2">
          <span className="text-xs sm:text-[11px] text-muted-foreground">Glob:</span>
          <code className="bg-muted/50 border border-border/50 px-2 py-0.5 rounded text-xs font-mono">
            {glob}
          </code>
        </div>
      )}
    </div>
  );
}

function TaskInputDisplay({ input, colorStyles }: ToolRendererProps) {
  const description = input.description as string | undefined;
  const subagent = input.subagent as string | undefined;
  const subagentType = input.subagent_type as string | undefined;

  return (
    <div className="space-y-2">
      {description && (
        <div className="space-y-1">
          <span className="text-xs sm:text-[11px] text-muted-foreground">Task:</span>
          <p className="text-xs text-foreground leading-relaxed">{description}</p>
        </div>
      )}
      {(subagent || subagentType) && (
        <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
          <span className="text-xs sm:text-[11px] text-muted-foreground">Delegating to:</span>
          {subagent && (
            <code
              className="px-1.5 sm:px-2 py-0.5 rounded text-xs font-mono bg-muted/50 border border-border/50"
              style={colorStyles?.badge}
            >
              {subagent}
            </code>
          )}
          {subagentType && (
            <span className="text-xs sm:text-[10px] px-1.5 py-0.5 rounded bg-muted/30 border border-border/50 text-muted-foreground">
              {subagentType}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function WebFetchInputDisplay({ input }: { input: Record<string, unknown> }) {
  const url = input.url as string | undefined;
  const query = input.query as string | undefined;

  return (
    <div className="space-y-2">
      {url && (
        <div className="space-y-1">
          <span className="text-xs sm:text-[11px] text-muted-foreground">Fetching from:</span>
          <code className="block text-xs font-mono bg-muted/50 border border-border/50 px-2 py-1.5 rounded break-all">
            {url}
          </code>
        </div>
      )}
      {query && (
        <div className="space-y-1">
          <span className="text-xs sm:text-[11px] text-muted-foreground">Query:</span>
          <p className="text-xs text-foreground leading-relaxed">{query}</p>
        </div>
      )}
    </div>
  );
}

function WebSearchInputDisplay({ input }: { input: Record<string, unknown> }) {
  const query = input.query as string | undefined;
  const url = input.url as string | undefined;

  return (
    <div className="space-y-2">
      {query && (
        <div className="space-y-1">
          <span className="text-xs sm:text-[11px] text-muted-foreground">Searching for:</span>
          <p className="text-xs text-foreground leading-relaxed font-medium">&quot;{query}&quot;</p>
        </div>
      )}
      {url && (
        <div className="space-y-1">
          <span className="text-xs sm:text-[11px] text-muted-foreground">Search engine:</span>
          <code className="text-xs font-mono bg-muted/50 border border-border/50 px-2 py-0.5 rounded">
            {url}
          </code>
        </div>
      )}
    </div>
  );
}

function AskUserQuestionInputDisplay({ input }: { input: Record<string, unknown> }) {
  const questions = input.questions as Array<{
    question: string;
    header?: string;
    options?: Array<{ label: string; description?: string }>;
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
            <div className="text-xs sm:text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              {q.header}
            </div>
          )}
          <div className="text-xs font-medium text-foreground">{q.question}</div>
          {q.options && q.options.length > 0 && (
            <div className="space-y-1.5 pl-2">
              {q.options.map((opt, oIdx) => (
                <div key={oIdx} className="flex items-start gap-2 text-[11px]">
                  <span className="text-muted-foreground/60 select-none mt-0.5">
                    {String.fromCharCode(65 + oIdx)}.
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-foreground">{opt.label}</div>
                    {opt.description && (
                      <div className="text-xs sm:text-[10px] text-muted-foreground mt-0.5 leading-snug">
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
              <span className="text-xs sm:text-[10px] px-1.5 py-0.5 rounded bg-muted/50 border border-border/50">
                {q.multiSelect ? 'Multiple selection' : 'Single selection'}
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function TodoWriteInputDisplay({ input }: { input: Record<string, unknown> }) {
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
                <div className="w-3 h-3 rounded-full bg-status-success flex items-center justify-center">
                  <svg
                    className="w-2 h-2 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={3}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-foreground">
                {todo.activeForm || todo.content}
              </div>
              {todo.activeForm && todo.activeForm !== todo.content && (
                <div className="text-xs sm:text-[10px] text-muted-foreground mt-0.5">
                  {todo.content}
                </div>
              )}
            </div>
            {todo.status && (
              <span
                className={cn(
                  'text-xs sm:text-[10px] px-1.5 py-0.5 rounded shrink-0',
                  isPending
                    ? 'bg-status-warning-bg text-status-warning border border-status-warning/20'
                    : 'bg-status-success-bg text-status-success border border-status-success/20'
                )}
              >
                {todo.status}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// --- Task Management Tool Displays ---

function TaskCreateInputDisplay({ input }: { input: Record<string, unknown> }) {
  const subject = input.subject as string | undefined;
  const description = input.description as string | undefined;
  const activeForm = input.activeForm as string | undefined;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Plus className="h-3.5 w-3.5 text-status-success" />
        <span className="text-xs font-medium text-foreground">
          {subject || 'New task'}
        </span>
      </div>
      {description && (
        <p className="text-xs sm:text-[11px] text-muted-foreground leading-relaxed pl-5">
          {description.length > 150 ? description.slice(0, 150) + '...' : description}
        </p>
      )}
      {activeForm && (
        <div className="flex items-center gap-1.5 pl-5">
          <span className="text-xs sm:text-[10px] text-muted-foreground italic">
            &quot;{activeForm}&quot;
          </span>
        </div>
      )}
    </div>
  );
}

function TaskUpdateInputDisplay({ input }: { input: Record<string, unknown> }) {
  const taskId = input.taskId as string | undefined;
  const status = input.status as string | undefined;
  const subject = input.subject as string | undefined;
  const owner = input.owner as string | undefined;
  const addBlocks = input.addBlocks as string[] | undefined;
  const addBlockedBy = input.addBlockedBy as string[] | undefined;

  const statusConfig: Record<string, { color: string; bg: string }> = {
    pending: { color: 'text-status-warning-fg', bg: 'bg-status-warning-bg' },
    in_progress: { color: 'text-status-info-fg', bg: 'bg-status-info-bg' },
    completed: { color: 'text-status-success-fg', bg: 'bg-status-success-bg' },
  };

  const statusStyle = status ? statusConfig[status] : null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
        <RefreshCw className="h-3.5 w-3.5 text-status-info" />
        <span className="text-xs sm:text-[11px] text-muted-foreground">
          Task
        </span>
        <code className="text-xs font-mono px-1.5 py-0.5 rounded bg-muted/50 border border-border/50">
          #{taskId}
        </code>
        {status && statusStyle && (
          <span
            className={cn(
              'text-xs sm:text-[10px] px-1.5 py-0.5 rounded font-medium',
              statusStyle.color,
              statusStyle.bg
            )}
          >
            {status.replace('_', ' ')}
          </span>
        )}
      </div>
      {subject && (
        <p className="text-xs font-medium text-foreground pl-5">{subject}</p>
      )}
      {owner && (
        <div className="flex items-center gap-1.5 pl-5 text-xs sm:text-[11px] text-muted-foreground">
          <span>Assigned to:</span>
          <code className="px-1.5 py-0.5 rounded bg-muted/50 font-mono">
            {owner}
          </code>
        </div>
      )}
      {addBlocks && addBlocks.length > 0 && (
        <div className="flex items-center gap-1.5 pl-5 text-xs sm:text-[11px] text-muted-foreground">
          <span>Blocks:</span>
          {addBlocks.map((id) => (
            <code key={id} className="px-1.5 py-0.5 rounded bg-muted/50 font-mono">
              #{id}
            </code>
          ))}
        </div>
      )}
      {addBlockedBy && addBlockedBy.length > 0 && (
        <div className="flex items-center gap-1.5 pl-5 text-xs sm:text-[11px] text-muted-foreground">
          <span>Blocked by:</span>
          {addBlockedBy.map((id) => (
            <code key={id} className="px-1.5 py-0.5 rounded bg-muted/50 font-mono">
              #{id}
            </code>
          ))}
        </div>
      )}
    </div>
  );
}

function TaskListInputDisplay() {
  return (
    <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-[11px] text-muted-foreground">
      <ListTodo className="h-3.5 w-3.5 text-purple-500" />
      <span>Listing all tasks</span>
    </div>
  );
}

function TaskGetInputDisplay({ input }: { input: Record<string, unknown> }) {
  const taskId = input.taskId as string | undefined;

  return (
    <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-[11px]">
      <FileSearch2 className="h-3.5 w-3.5 text-status-info" />
      <span className="text-muted-foreground">Getting task</span>
      <code className="px-1.5 py-0.5 rounded bg-muted/50 border border-border/50 font-mono">
        #{taskId}
      </code>
    </div>
  );
}

function JsonInputDisplay({ input }: { input: Record<string, unknown> }) {
  return (
    <pre className="bg-muted/40 border border-border/50 p-2 sm:p-3 rounded text-xs font-mono overflow-auto max-h-48 sm:max-h-64 whitespace-pre-wrap break-all">
      {JSON.stringify(input, null, 2)}
    </pre>
  );
}

/**
 * Display tool result content with proper formatting.
 */
export function ToolResultDisplay({
  content,
  isError,
}: {
  content: string;
  isError?: boolean;
}) {
  if (!content) return null;

  // Try to parse as JSON for pretty display
  let formattedContent = content;
  let isJson = false;
  try {
    const parsed = JSON.parse(content);
    formattedContent = JSON.stringify(parsed, null, 2);
    isJson = true;
  } catch {
    // Not JSON, use as-is
  }

  const lines = formattedContent.split('\n');
  const isLong = lines.length > 10;
  const preview = isLong ? lines.slice(0, 10).join('\n') + '\n...' : formattedContent;

  return (
    <pre
      className={cn(
        'text-xs sm:text-[11px] font-mono whitespace-pre-wrap break-all rounded p-1.5 sm:p-2 max-h-48 sm:max-h-64 overflow-auto',
        isError
          ? 'bg-destructive/5 text-destructive border border-destructive/20'
          : 'bg-muted/30 text-foreground border border-border/30'
      )}
    >
      {isJson ? <code>{formattedContent}</code> : <code>{preview}</code>}
    </pre>
  );
}
