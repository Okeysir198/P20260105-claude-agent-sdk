'use client';

import { cn } from '@/lib/utils';
import { CheckCircle2, CircleDot, Circle, Bot } from 'lucide-react';
import type { KanbanTask } from '@/lib/store/kanban-store';

interface KanbanCardProps {
  task: KanbanTask;
}

function TaskStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-3 w-3 text-status-success shrink-0" />;
    case 'in_progress':
      return <CircleDot className="h-3 w-3 text-status-info animate-pulse shrink-0" />;
    default:
      return <Circle className="h-3 w-3 text-status-warning animate-pulse shrink-0" />;
  }
}

function OwnerBadge({ owner }: { owner?: string }) {
  if (!owner) return null;

  const colorClass = owner === 'main'
    ? 'bg-muted text-muted-foreground'
    : owner.startsWith('test')
      ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
      : owner === 'explore' || owner === 'Explore'
        ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400'
        : 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400';

  return (
    <span className={cn('inline-flex items-center gap-0.5 text-[9px] px-1 py-0.5 rounded', colorClass)}>
      <Bot className="h-2.5 w-2.5" />
      {owner}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const badgeClass = cn(
    'text-[9px] px-1 py-0.5 rounded shrink-0',
    status === 'completed' && 'bg-status-success-bg text-status-success border border-status-success/20',
    status === 'in_progress' && 'bg-status-info-bg text-status-info border border-status-info/20 animate-pulse',
    (!status || status === 'pending') && 'bg-status-warning-bg text-status-warning-fg border border-status-warning/20 animate-pulse'
  );
  return <span className={badgeClass}>{status || 'pending'}</span>;
}

export function KanbanCard({ task }: KanbanCardProps) {
  return (
    <div
      className={cn(
        'rounded-md border bg-card p-2 shadow-sm transition-all',
        task.status === 'in_progress' && 'border-status-info/30 shadow-status-info/5'
      )}
    >
      <div className="flex items-start gap-1.5">
        <TaskStatusIcon status={task.status} />
        <div className="min-w-0 flex-1">
          <p className={cn(
            'text-[11px] font-medium leading-tight',
            task.status === 'completed' && 'line-through text-muted-foreground'
          )}>
            {task.subject}
          </p>
          {task.description && task.description !== task.subject && (
            <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">
              {task.description}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-dashed">
        <OwnerBadge owner={task.owner} />
        <StatusBadge status={task.status} />
      </div>
    </div>
  );
}
