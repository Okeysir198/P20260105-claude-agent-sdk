'use client';

import { cn, formatTime } from '@/lib/utils';
import {
  CheckCircle2, CircleDot, Circle, Bot,
  FolderTree, ListPlus, CheckSquare,
} from 'lucide-react';
import { getAgentColor } from './agent-colors';
import type { KanbanTask } from '@/lib/store/kanban-store';

interface KanbanCardProps {
  task: KanbanTask;
  onSelect?: (task: KanbanTask) => void;
}

const SOURCE_ICONS: Record<string, { icon: typeof FolderTree; label: string }> = {
  Task: { icon: FolderTree, label: 'Subagent delegation' },
  TaskCreate: { icon: ListPlus, label: 'Created task' },
  TodoWrite: { icon: CheckSquare, label: 'Todo item' },
};

function TaskStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-3.5 w-3.5 text-status-success shrink-0" />;
    case 'in_progress':
      return <CircleDot className="h-3.5 w-3.5 text-status-info animate-pulse shrink-0" />;
    default:
      return <Circle className="h-3.5 w-3.5 text-status-warning shrink-0" />;
  }
}

function SourceIcon({ source }: { source: string }) {
  const sourceConfig = SOURCE_ICONS[source];
  if (!sourceConfig) return null;

  const Icon = sourceConfig.icon;
  return (
    <span title={sourceConfig.label} className="text-muted-foreground">
      <Icon className="h-3 w-3" />
    </span>
  );
}

function OwnerBadge({ owner }: { owner?: string }) {
  if (!owner) return null;
  return (
    <span className={cn(
      'inline-flex items-center gap-1 text-[9px] font-medium px-1.5 py-0.5 rounded-full border min-w-0 overflow-hidden',
      getAgentColor(owner)
    )}>
      <Bot className="h-2.5 w-2.5 shrink-0" />
      <span className="truncate">{owner}</span>
    </span>
  );
}

export function KanbanCard({ task, onSelect }: KanbanCardProps) {
  return (
    <button
      type="button"
      className={cn(
        'w-full text-left rounded-lg border bg-card p-2.5 shadow-sm transition-all',
        'hover:shadow-md hover:border-foreground/10 active:scale-[0.98]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        task.status === 'in_progress' && 'border-status-info/30 bg-status-info/[0.02]',
        task.status === 'completed' && 'opacity-75'
      )}
      onClick={() => onSelect?.(task)}
      aria-label={`Task: ${task.subject}, status: ${task.status}`}
    >
      {/* Top row: status icon + subject + source icon */}
      <div className="flex items-start gap-2">
        <TaskStatusIcon status={task.status} />
        <div className="min-w-0 flex-1">
          <p className={cn(
            'text-[11px] font-semibold leading-snug',
            task.status === 'completed' && 'line-through text-muted-foreground'
          )}>
            {task.subject}
          </p>
          {/* Active form text when in progress */}
          {task.status === 'in_progress' && task.activeForm && task.activeForm !== task.subject && (
            <p className="text-[10px] text-status-info mt-0.5 truncate italic">
              {task.activeForm}
            </p>
          )}
          {/* Description */}
          {task.description && task.description !== task.subject && task.description !== task.activeForm && (
            <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2 leading-relaxed">
              {task.description}
            </p>
          )}
        </div>
        <SourceIcon source={task.source} />
      </div>

      {/* Bottom row: owner + delegation + time */}
      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-dashed border-border/50 gap-1.5">
        <div className="flex items-center gap-1.5 min-w-0 overflow-hidden">
          <OwnerBadge owner={task.owner} />
          {task.delegatedTo && (
            <span className="inline-flex items-center gap-0.5 text-[9px] text-muted-foreground" title={`Delegated to ${task.delegatedTo} subagent`}>
              <FolderTree className="h-2.5 w-2.5" />
            </span>
          )}
        </div>
        {task.timestamp && (
          <span className="text-[9px] text-muted-foreground tabular-nums shrink-0">
            {formatTime(task.timestamp)}
          </span>
        )}
      </div>
    </button>
  );
}
