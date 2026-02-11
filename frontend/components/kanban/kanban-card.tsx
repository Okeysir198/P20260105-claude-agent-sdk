'use client';

import { createElement } from 'react';
import { cn } from '@/lib/utils';
import {
  CheckCircle2, CircleDot, Circle, Bot,
  FolderTree, ListPlus, CheckSquare,
} from 'lucide-react';
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
  const config = SOURCE_ICONS[source];
  if (!config) return null;

  return (
    <span title={config.label} className="text-muted-foreground">
      {createElement(config.icon, { className: 'h-3 w-3' })}
    </span>
  );
}

const OWNER_COLORS: Record<string, string> = {
  main: 'bg-muted/80 text-muted-foreground border-border',
  explore: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
  Explore: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
};

function getOwnerColor(owner: string): string {
  if (OWNER_COLORS[owner]) return OWNER_COLORS[owner];
  if (owner.startsWith('test')) return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
  if (owner.includes('code') || owner.includes('lean')) return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
  return 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20';
}

function OwnerBadge({ owner }: { owner?: string }) {
  if (!owner) return null;
  return (
    <span className={cn(
      'inline-flex items-center gap-1 text-[9px] font-medium px-1.5 py-0.5 rounded-full border',
      getOwnerColor(owner)
    )}>
      <Bot className="h-2.5 w-2.5" />
      <span className="max-w-[80px] truncate">{owner}</span>
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label = status === 'in_progress' ? 'active' : status || 'pending';
  const badgeClass = cn(
    'text-[9px] font-medium px-1.5 py-0.5 rounded-full shrink-0 border',
    status === 'completed' && 'bg-status-success/10 text-status-success border-status-success/20',
    status === 'in_progress' && 'bg-status-info/10 text-status-info border-status-info/20 animate-pulse',
    (!status || status === 'pending') && 'bg-status-warning/10 text-status-warning-fg border-status-warning/20'
  );
  return <span className={badgeClass}>{label}</span>;
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

      {/* Bottom row: owner + delegation + status */}
      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-dashed border-border/50 gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <OwnerBadge owner={task.owner} />
          {task.delegatedTo && (
            <span className="inline-flex items-center gap-0.5 text-[9px] text-muted-foreground" title={`Delegated to ${task.delegatedTo} subagent`}>
              <FolderTree className="h-2.5 w-2.5" />
            </span>
          )}
        </div>
        <StatusBadge status={task.status} />
      </div>
    </button>
  );
}
