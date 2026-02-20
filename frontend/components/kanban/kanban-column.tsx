'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { KanbanCard } from './kanban-card';
import { ChevronDown, ChevronRight, Circle, CircleDot, CheckCircle2 } from 'lucide-react';
import type { KanbanTask } from '@/lib/store/kanban-store';

interface KanbanColumnProps {
  title: string;
  status: 'pending' | 'in_progress' | 'completed';
  tasks: KanbanTask[];
  onSelectTask?: (task: KanbanTask) => void;
  defaultExpanded?: boolean;
}

const STATUS_CONFIG: Record<string, { color: string; icon: typeof Circle; bg: string }> = {
  pending: { color: 'text-status-warning', icon: Circle, bg: 'bg-status-warning/10' },
  in_progress: { color: 'text-status-info', icon: CircleDot, bg: 'bg-status-info/10' },
  completed: { color: 'text-status-success', icon: CheckCircle2, bg: 'bg-status-success/10' },
};

export function KanbanColumn({ title, status, tasks, onSelectTask, defaultExpanded }: KanbanColumnProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded || status !== 'completed' || tasks.length <= 3);
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const StatusIcon = cfg.icon;

  const alwaysExpanded = !!defaultExpanded;

  return (
    <div className="min-w-0">
      {alwaysExpanded ? (
        <div className="flex items-center gap-1.5 w-full px-2 py-1.5">
          <StatusIcon className={cn('h-3 w-3 shrink-0', cfg.color)} />
          <span className={cn('text-[11px] font-semibold uppercase tracking-wider truncate min-w-0', cfg.color)}>
            {title}
          </span>
          <span className={cn(
            'text-[10px] font-medium px-1.5 py-0.5 rounded-full ml-auto shrink-0',
            cfg.bg, cfg.color
          )}>
            {tasks.length}
          </span>
        </div>
      ) : (
        <button
          className="flex items-center gap-1.5 w-full text-left px-2 py-1.5 rounded-md hover:bg-muted/50 transition-colors cursor-pointer"
          onClick={() => setIsExpanded(!isExpanded)}
          type="button"
        >
          {isExpanded
            ? <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
            : <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />}
          <StatusIcon className={cn('h-3 w-3 shrink-0', cfg.color)} />
          <span className={cn('text-[11px] font-semibold uppercase tracking-wider truncate min-w-0', cfg.color)}>
            {title}
          </span>
          <span className={cn(
            'text-[10px] font-medium px-1.5 py-0.5 rounded-full ml-auto',
            cfg.bg, cfg.color
          )}>
            {tasks.length}
          </span>
        </button>
      )}

      {(alwaysExpanded || isExpanded) && (
        <div className="space-y-1.5 mt-1 px-0.5">
          {tasks.length === 0 ? (
            <div className="text-[11px] text-muted-foreground/60 italic px-2 py-3 text-center border border-dashed rounded-md">
              No tasks
            </div>
          ) : (
            tasks.map((task) => (
              <KanbanCard key={task.id} task={task} onSelect={onSelectTask} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
