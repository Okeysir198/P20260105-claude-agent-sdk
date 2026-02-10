'use client';

import { createElement, useState } from 'react';
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
} from 'lucide-react';
import { useKanbanStore } from '@/lib/store/kanban-store';
import type { KanbanTask, AgentToolCall } from '@/lib/store/kanban-store';

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

function tryFormatJson(value: string): string {
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function CollapsibleContent({
  icon,
  label,
  content,
}: {
  icon: typeof Code2;
  label: string;
  content: string;
}) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="pt-3">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors w-full"
      >
        {expanded
          ? <ChevronDown className="h-3.5 w-3.5" />
          : <ChevronRight className="h-3.5 w-3.5" />
        }
        {createElement(icon, { className: 'h-3.5 w-3.5' })}
        <span>{label}</span>
      </button>
      {expanded && (
        <pre className="mt-2 bg-muted rounded-md p-3 text-xs font-mono max-h-64 overflow-auto whitespace-pre-wrap break-all">
          {content}
        </pre>
      )}
    </div>
  );
}

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
            {toolCall.agent === 'main' ? 'Main Agent' : toolCall.agent}
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
          content={tryFormatJson(toolCall.resultContent)}
        />
      )}

      <UsageSummary />
    </div>
  );
}

export function KanbanDetailModal({ task, toolCall, onClose }: KanbanDetailModalProps) {
  const isOpen = !!(task || toolCall);

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
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
              {createElement(sourceIcon, { className: 'h-4 w-4 text-muted-foreground' })}
            </div>
            <div className="min-w-0">
              <DialogTitle className="text-sm font-semibold truncate">{title}</DialogTitle>
              <DialogDescription className="text-xs">
                {task ? (SOURCE_LABELS[task.source] || 'Task') : 'Tool Call Details'}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="mt-2 max-h-[80vh] overflow-y-auto">
          {task && <TaskDetail task={task} />}
          {toolCall && <ToolCallDetail toolCall={toolCall} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}
