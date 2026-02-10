'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { KanbanCard } from './kanban-card';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { KanbanTask } from '@/lib/store/kanban-store';

interface KanbanColumnProps {
  title: string;
  status: 'pending' | 'in_progress' | 'completed';
  tasks: KanbanTask[];
  collapsible?: boolean;
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'text-status-warning',
  in_progress: 'text-status-info',
  completed: 'text-status-success',
};

export function KanbanColumn({ title, status, tasks, collapsible }: KanbanColumnProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="min-w-0">
      <button
        className={cn(
          'flex items-center gap-1.5 w-full text-left px-1.5 py-1 rounded',
          collapsible && 'hover:bg-muted/50 cursor-pointer',
          !collapsible && 'cursor-default'
        )}
        onClick={() => collapsible && setIsExpanded(!isExpanded)}
        type="button"
      >
        {collapsible && (
          isExpanded
            ? <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
            : <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
        )}
        <span className={cn('text-[10px] font-semibold uppercase tracking-wider', STATUS_STYLES[status])}>
          {title}
        </span>
        <span className="text-[10px] text-muted-foreground">({tasks.length})</span>
      </button>

      {isExpanded && (
        <div className="space-y-1.5 mt-1.5">
          {tasks.length === 0 ? (
            <div className="text-[10px] text-muted-foreground italic px-1.5 py-2">
              No tasks
            </div>
          ) : (
            tasks.map((task) => <KanbanCard key={task.id} task={task} />)
          )}
        </div>
      )}
    </div>
  );
}
