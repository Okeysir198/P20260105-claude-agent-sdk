'use client';

import { createElement, useState, useCallback, useRef, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { getToolConfig, getToolColorStyles } from '@/lib/tool-config';
import { cn, formatTime } from '@/lib/utils';
import {
  CheckCircle2, CircleDot, Circle, Bot,
  FolderTree, ListPlus, CheckSquare, Clock,
  Wrench, Hash, FileText, User, Tag,
  Code2, FileOutput, ChevronDown, ChevronRight,
  Copy, Check,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from '@/components/chat/code-block';
import { useKanbanStore } from '@/lib/store/kanban-store';
import type { KanbanTask, AgentToolCall } from '@/lib/store/kanban-store';

// === Shared Components ===

interface KanbanDetailModalProps {
  task: KanbanTask | null;
  toolCall: AgentToolCall | null;
  onClose: () => void;
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-status-success" />;
    case 'in_progress':
    case 'running':
      return <CircleDot className="h-5 w-5 text-status-info animate-pulse" />;
    case 'error':
      return <CircleDot className="h-5 w-5 text-status-error" />;
    default:
      return <Circle className="h-5 w-5 text-status-warning" />;
  }
}

function DetailRow({ icon, label, children }: { icon: typeof Hash; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <div className="flex items-center gap-2 shrink-0 w-24 text-muted-foreground">
        {createElement(icon, { className: 'h-3.5 w-3.5' })}
        <span className="text-xs">{label}</span>
      </div>
      <div className="flex-1 min-w-0 text-sm">{children}</div>
    </div>
  );
}

const SOURCE_LABELS: Record<string, string> = {
  Task: 'Subagent Delegation',
  TaskCreate: 'Task Created',
  TodoWrite: 'Todo Item',
};

function StatusBadgeLarge({ status }: { status: string }) {
  const label = status === 'in_progress' ? 'In Progress' : status === 'running' ? 'Running' : status.charAt(0).toUpperCase() + status.slice(1);
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border',
      status === 'completed' && 'bg-status-success/10 text-status-success border-status-success/20',
      (status === 'in_progress' || status === 'running') && 'bg-status-info/10 text-status-info border-status-info/20',
      status === 'error' && 'bg-status-error/10 text-status-error border-status-error/20',
      status === 'pending' && 'bg-status-warning/10 text-status-warning-fg border-status-warning/20',
    )}>
      <StatusIcon status={status} />
      {label}
    </span>
  );
}

// === Copy Button ===

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={cn(
        'flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] transition-colors shrink-0',
        copied ? 'text-status-success' : 'text-muted-foreground hover:text-foreground'
      )}
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      <span>{copied ? 'Copied' : 'Copy'}</span>
    </button>
  );
}

// === Markdown Output Renderer ===

const markdownComponents: Record<string, React.ComponentType<any>> = {
  code: ({ className, children }: { className?: string; children?: React.ReactNode }) => {
    const languageMatch = className?.match(/language-(\w+)/);
    const language = languageMatch ? languageMatch[1] : null;
    const inline = !language;

    let codeContent = '';
    if (typeof children === 'string') {
      codeContent = children;
    } else if (Array.isArray(children)) {
      codeContent = children.map((c: unknown) => typeof c === 'string' ? c : String(c || '')).join('');
    } else {
      codeContent = String(children || '');
    }

    if (!inline) {
      return <CodeBlock code={codeContent.trim()} language={language} />;
    }

    return (
      <code className="px-1.5 py-0.5 rounded bg-muted/50 border border-border/50 text-xs font-mono text-foreground">
        {codeContent}
      </code>
    );
  },
  pre: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  p: ({ children }: { children?: React.ReactNode }) => <p className="my-1.5">{children}</p>,
  a: ({ children, href }: { children?: React.ReactNode; href?: string }) => (
    <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>
  ),
  h1: ({ children }: { children?: React.ReactNode }) => <h1 className="text-lg font-semibold mt-4 mb-2">{children}</h1>,
  h2: ({ children }: { children?: React.ReactNode }) => <h2 className="text-base font-semibold mt-4 mb-2">{children}</h2>,
  h3: ({ children }: { children?: React.ReactNode }) => <h3 className="text-sm font-semibold mt-3 mb-1">{children}</h3>,
  ul: ({ children }: { children?: React.ReactNode }) => <ul className="list-disc pl-5 my-2 space-y-0.5">{children}</ul>,
  ol: ({ children }: { children?: React.ReactNode }) => <ol className="list-decimal pl-5 my-2 space-y-0.5">{children}</ol>,
  li: ({ children }: { children?: React.ReactNode }) => <li className="leading-relaxed">{children}</li>,
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-4 border-primary pl-3 italic text-muted-foreground my-3">{children}</blockquote>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto my-3">
      <table className="min-w-full divide-y divide-border text-xs">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: React.ReactNode }) => <th className="px-2 py-1 text-left font-medium bg-muted/50">{children}</th>,
  td: ({ children }: { children?: React.ReactNode }) => <td className="px-2 py-1 border-t border-border/50">{children}</td>,
};

function MarkdownOutput({ content }: { content: string }) {
  const processedContent = useMemo(() => {
    const trimmed = content.trim();
    // If content looks like raw JSON, wrap in a json code fence
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
        (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        const formatted = JSON.stringify(JSON.parse(trimmed), null, 2);
        return '```json\n' + formatted + '\n```';
      } catch { /* not valid JSON, render as-is */ }
    }
    return content;
  }, [content]);

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none p-3 prose-p:text-foreground prose-headings:text-foreground prose-strong:text-foreground prose-a:text-primary text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}

// === Collapsible Content Section (Input / Output) ===

function CollapsibleContent({
  icon,
  label,
  content,
  isOutput = false,
}: {
  icon: typeof Code2;
  label: string;
  content: string;
  isOutput?: boolean;
}) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="pt-3">
      {/* Header: toggle + label + copy */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded
            ? <ChevronDown className="h-3.5 w-3.5" />
            : <ChevronRight className="h-3.5 w-3.5" />
          }
          {createElement(icon, { className: 'h-3.5 w-3.5' })}
          <span>{label}</span>
        </button>
        <CopyButton text={content} />
      </div>

      {/* Content area — height resizable, scrollable */}
      {expanded && (
        <div
          className={cn(
            'mt-2 rounded-md border border-border overflow-auto',
            isOutput && 'resize-y min-h-[80px]'
          )}
          style={isOutput ? { height: 240, maxHeight: '60vh' } : { maxHeight: '40vh' }}
        >
          {isOutput ? (
            <MarkdownOutput content={content} />
          ) : (
            <pre className="p-3 text-xs font-mono bg-muted/50 whitespace-pre-wrap break-all">
              {content}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// === Usage Summary ===

function UsageSummary() {
  const sessionUsage = useKanbanStore((s) => s.sessionUsage);
  if (!sessionUsage) return null;

  return (
    <div className="pt-3 mt-2 border-t border-border/50">
      <p className="text-[10px] font-medium text-muted-foreground mb-2">Session Usage</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px]">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Cost</span>
          <span className="font-mono">${sessionUsage.totalCostUsd.toFixed(4)}</span>
        </div>
        {sessionUsage.inputTokens !== undefined && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Input</span>
            <span className="font-mono">{sessionUsage.inputTokens.toLocaleString()}</span>
          </div>
        )}
        {sessionUsage.outputTokens !== undefined && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Output</span>
            <span className="font-mono">{sessionUsage.outputTokens.toLocaleString()}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-muted-foreground">Duration</span>
          <span className="font-mono">{(sessionUsage.durationMs / 1000).toFixed(1)}s</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">API Time</span>
          <span className="font-mono">{(sessionUsage.durationApiMs / 1000).toFixed(1)}s</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Turns</span>
          <span className="font-mono">{sessionUsage.turnCount}</span>
        </div>
        {sessionUsage.cacheReadInputTokens !== undefined && sessionUsage.cacheReadInputTokens > 0 && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Cache Read</span>
            <span className="font-mono">{sessionUsage.cacheReadInputTokens.toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// === Task Detail ===

function TaskDetail({ task }: { task: KanbanTask }) {
  return (
    <div className="space-y-1">
      <div className="divide-y divide-border/50">
        <DetailRow icon={Tag} label="Status">
          <StatusBadgeLarge status={task.status} />
        </DetailRow>

        {task.description && task.description !== task.subject && (
          <DetailRow icon={FileText} label="Description">
            <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{task.description}</p>
          </DetailRow>
        )}

        {task.activeForm && task.status === 'in_progress' && (
          <DetailRow icon={Clock} label="Activity">
            <p className="text-sm text-status-info italic">{task.activeForm}</p>
          </DetailRow>
        )}

        <DetailRow icon={User} label="Owner">
          {task.owner ? (
            <span className="inline-flex items-center gap-1 text-sm">
              <Bot className="h-3.5 w-3.5 text-muted-foreground" />
              {task.owner}
            </span>
          ) : (
            <span className="text-muted-foreground text-sm">Unassigned</span>
          )}
        </DetailRow>

        <DetailRow icon={Wrench} label="Source">
          <span className="text-sm text-muted-foreground">{SOURCE_LABELS[task.source] || task.source}</span>
        </DetailRow>

        {task.delegatedTo && (
          <DetailRow icon={FolderTree} label="Delegated to">
            <span className="inline-flex items-center gap-1 text-sm">
              <Bot className="h-3.5 w-3.5 text-muted-foreground" />
              {task.delegatedTo} subagent
            </span>
          </DetailRow>
        )}

        <DetailRow icon={Hash} label="ID">
          <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">{task.id}</code>
        </DetailRow>
      </div>

      {task.toolInput && Object.keys(task.toolInput).length > 0 && (
        <CollapsibleContent
          icon={Code2}
          label="Tool Input"
          content={JSON.stringify(task.toolInput, null, 2)}
        />
      )}

      <UsageSummary />
    </div>
  );
}

// === Tool Call Detail ===

function ToolCallDetail({ toolCall }: { toolCall: AgentToolCall }) {
  const config = getToolConfig(toolCall.toolName);
  const colorStyles = getToolColorStyles(toolCall.toolName);

  return (
    <div className="space-y-1">
      <div className="divide-y divide-border/50">
        <DetailRow icon={Tag} label="Status">
          <StatusBadgeLarge status={toolCall.status} />
        </DetailRow>

        <DetailRow icon={Wrench} label="Tool">
          <div className="flex items-center gap-2">
            <div
              className="h-5 w-5 rounded flex items-center justify-center"
              style={colorStyles.iconBg}
            >
              {createElement(config.icon, { className: 'h-3 w-3', style: colorStyles.iconText })}
            </div>
            <span className="text-sm font-medium">{toolCall.toolName}</span>
          </div>
        </DetailRow>

        {toolCall.summary && (
          <DetailRow icon={FileText} label="Summary">
            <p className="text-sm text-foreground break-all">{toolCall.summary}</p>
          </DetailRow>
        )}

        <DetailRow icon={User} label="Agent">
          <span className="inline-flex items-center gap-1 text-sm">
            <Bot className="h-3.5 w-3.5 text-muted-foreground" />
            {toolCall.agent === 'main' ? 'Main Agent' : `Sub-Agent: ${toolCall.agent}`}
          </span>
        </DetailRow>

        <DetailRow icon={Clock} label="Time">
          <span className="text-sm tabular-nums">{formatTime(toolCall.timestamp)}</span>
        </DetailRow>

        <DetailRow icon={Hash} label="ID">
          <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded break-all">{toolCall.id}</code>
        </DetailRow>
      </div>

      {toolCall.toolInput && Object.keys(toolCall.toolInput).length > 0 && (
        <CollapsibleContent
          icon={Code2}
          label="Input"
          content={JSON.stringify(toolCall.toolInput, null, 2)}
        />
      )}

      {toolCall.resultContent && (
        <CollapsibleContent
          icon={FileOutput}
          label="Output"
          content={toolCall.resultContent}
          isOutput
        />
      )}

      <UsageSummary />
    </div>
  );
}

// === Modal ===

export function KanbanDetailModal({ task, toolCall, onClose }: KanbanDetailModalProps) {
  const isOpen = !!(task || toolCall);
  const [modalWidth, setModalWidth] = useState(560);
  const resizeRef = useRef({ startX: 0, startWidth: 0 });

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    resizeRef.current = { startX: e.clientX, startWidth: modalWidth };
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';

    const onMove = (ev: MouseEvent) => {
      const delta = ev.clientX - resizeRef.current.startX;
      // x2 because dialog is centered — expanding right also extends left
      const newWidth = Math.max(400, Math.min(window.innerWidth * 0.9, resizeRef.current.startWidth + delta * 2));
      setModalWidth(newWidth);
    };

    const onUp = () => {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [modalWidth]);

  const title = task
    ? task.subject
    : toolCall
      ? `${toolCall.toolName} Call`
      : '';

  const sourceIcon = task
    ? (task.source === 'Task' ? FolderTree : task.source === 'TaskCreate' ? ListPlus : CheckSquare)
    : toolCall
      ? getToolConfig(toolCall.toolName).icon
      : Wrench;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent
        className="sm:max-w-none !p-0 overflow-hidden"
        style={{ width: modalWidth }}
      >
        {/* Right edge resize handle */}
        <div
          className="absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize z-10 group/resize"
          onMouseDown={handleResizeStart}
        >
          <div className="absolute right-0 top-1/2 -translate-y-1/2 h-10 w-1 rounded-full bg-border group-hover/resize:bg-primary/50 transition-colors" />
        </div>

        {/* Left edge resize handle */}
        <div
          className="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize z-10 group/resize-l"
          onMouseDown={(e) => {
            e.preventDefault();
            resizeRef.current = { startX: e.clientX, startWidth: modalWidth };
            document.body.style.cursor = 'ew-resize';
            document.body.style.userSelect = 'none';

            const onMove = (ev: MouseEvent) => {
              const delta = resizeRef.current.startX - ev.clientX;
              const newWidth = Math.max(400, Math.min(window.innerWidth * 0.9, resizeRef.current.startWidth + delta * 2));
              setModalWidth(newWidth);
            };

            const onUp = () => {
              document.body.style.cursor = '';
              document.body.style.userSelect = '';
              document.removeEventListener('mousemove', onMove);
              document.removeEventListener('mouseup', onUp);
            };

            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
          }}
        >
          <div className="absolute left-0 top-1/2 -translate-y-1/2 h-10 w-1 rounded-full bg-border group-hover/resize-l:bg-primary/50 transition-colors" />
        </div>

        <div className="px-6 pt-6 pb-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                {createElement(sourceIcon, { className: 'h-4 w-4 text-muted-foreground' })}
              </div>
              <div className="min-w-0 flex-1">
                <DialogTitle className="text-sm font-semibold truncate">{title}</DialogTitle>
                <DialogDescription className="text-xs">
                  {task ? (SOURCE_LABELS[task.source] || 'Task') : 'Tool Call Details'}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
        </div>

        <div className="px-6 pb-6 pt-2 max-h-[80vh] overflow-y-auto">
          {task && <TaskDetail task={task} />}
          {toolCall && <ToolCallDetail toolCall={toolCall} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}
