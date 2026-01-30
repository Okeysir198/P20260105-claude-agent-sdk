'use client';

import type { ChatMessage } from '@/types';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getToolColorStyles } from '@/lib/tool-config';
import { CheckCircle2, CircleDot, Circle } from 'lucide-react';
import { NonCollapsibleToolCard } from './tool-card';
import { RunningIndicator } from './tool-status-badge';

interface TodoWriteDisplayProps {
  message: ChatMessage;
  isRunning: boolean;
  ToolIcon: LucideIcon;
  colorStyles: ReturnType<typeof getToolColorStyles>;
}

/**
 * Special display for TodoWrite - always visible task list (no accordion)
 */
export function TodoWriteDisplay({
  message,
  isRunning,
  ToolIcon,
  colorStyles,
}: TodoWriteDisplayProps) {
  const todos = message.toolInput?.todos as
    | Array<{
        content?: string;
        subject?: string;
        status?: string;
        activeForm?: string;
      }>
    | undefined;

  const completedCount = todos?.filter((t) => t.status === 'completed').length || 0;
  const totalCount = todos?.length || 0;

  return (
    <NonCollapsibleToolCard
      toolName="TodoWrite"
      ToolIcon={ToolIcon}
      color={colorStyles.iconText?.color}
      isRunning={isRunning}
      timestamp={message.timestamp}
      ariaLabel={`Todo list with ${totalCount} tasks, ${completedCount} completed${isRunning ? ', currently updating' : ''}`}
      headerContent={
        <>
          {todos && todos.length > 0 && (
            <span className="text-[10px] text-muted-foreground" aria-hidden="true">
              {todos.length} {todos.length === 1 ? 'task' : 'tasks'}
            </span>
          )}
          {isRunning && (
            <span className="ml-auto">
              <RunningIndicator label="Running" />
            </span>
          )}
        </>
      }
    >
      <TodoList todos={todos} />
    </NonCollapsibleToolCard>
  );
}

interface TodoListProps {
  todos?: Array<{
    content?: string;
    subject?: string;
    status?: string;
    activeForm?: string;
  }>;
}

/**
 * Displays a list of todo items with status indicators
 */
function TodoList({ todos }: TodoListProps) {
  return (
    <ul className="p-2 space-y-1 list-none" role="list" aria-label="Task list">
      {!todos || todos.length === 0 ? (
        <li className="text-[11px] text-muted-foreground italic px-2 py-1">No todos defined</li>
      ) : (
        todos.map((todo, idx) => <TodoItem key={idx} todo={todo} index={idx} />)
      )}
    </ul>
  );
}

interface TodoItemProps {
  todo: {
    content?: string;
    subject?: string;
    status?: string;
    activeForm?: string;
  };
  index: number;
}

/**
 * Individual todo item with status icon and badge
 */
function TodoItem({ todo, index }: TodoItemProps) {
  const isCompleted = todo.status === 'completed';
  const isInProgress = todo.status === 'in_progress';
  const taskName = todo.subject || todo.content || todo.activeForm || 'Unnamed task';
  const statusText = isCompleted ? 'completed' : isInProgress ? 'in progress' : 'pending';

  return (
    <li
      className="flex items-center gap-2 text-[11px] px-2 py-1.5 rounded hover:bg-muted/30 transition-colors"
      aria-label={`Task ${index + 1}: ${taskName}, status: ${statusText}`}
    >
      <div className="shrink-0" aria-hidden="true">
        <TodoStatusIcon status={todo.status} />
      </div>
      <div
        className={cn(
          'flex-1 min-w-0 truncate font-medium',
          isCompleted && 'line-through text-muted-foreground'
        )}
      >
        {taskName}
      </div>
      <span aria-hidden="true">
        <TodoStatusBadge status={todo.status} />
      </span>
    </li>
  );
}

/**
 * Status icon for todo items
 */
function TodoStatusIcon({ status }: { status?: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-3.5 w-3.5 text-status-success" />;
    case 'in_progress':
      return <CircleDot className="h-3.5 w-3.5 text-status-info animate-pulse" />;
    default:
      return <Circle className="h-3.5 w-3.5 text-status-warning animate-pulse" />;
  }
}

/**
 * Status badge for todo items
 */
function TodoStatusBadge({ status }: { status?: string }) {
  const statusText = status || 'pending';
  const badgeClass = cn(
    'text-[10px] px-1.5 py-0.5 rounded shrink-0',
    status === 'completed' && 'bg-status-success-bg text-status-success border border-status-success/20',
    status === 'in_progress' && 'bg-status-info-bg text-status-info border border-status-info/20 animate-pulse',
    (!status || status === 'pending') &&
      'bg-status-warning-bg text-status-warning-fg border border-status-warning/20 animate-pulse'
  );
  return <span className={badgeClass}>{statusText}</span>;
}
