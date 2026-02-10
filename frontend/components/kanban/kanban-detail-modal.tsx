'use client';

import { createElement } from 'react';
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
} from 'lucide-react';
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

function TaskDetail({ task }: { task: KanbanTask }) {
  return (
    <div className="space-y-1 divide-y divide-border/50">
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
  );
}

function ToolCallDetail({ toolCall }: { toolCall: AgentToolCall }) {
  const config = getToolConfig(toolCall.toolName);
  const colorStyles = getToolColorStyles(toolCall.toolName);

  return (
    <div className="space-y-1 divide-y divide-border/50">
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
      <DialogContent className="sm:max-w-md">
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

        <div className="mt-2">
          {task && <TaskDetail task={task} />}
          {toolCall && <ToolCallDetail toolCall={toolCall} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}
