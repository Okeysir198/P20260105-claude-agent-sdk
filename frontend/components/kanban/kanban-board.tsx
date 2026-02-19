'use client';

import React, { useState } from 'react';
import { useKanbanStore } from '@/lib/store/kanban-store';
import { useChatStore } from '@/lib/store/chat-store';
import { useWebSocket } from '@/hooks/use-websocket';
import { KanbanColumn } from './kanban-column';
import { AgentActivity } from './agent-activity';
import type { ActivityViewMode } from './agent-activity';
import { KanbanDetailModal } from './kanban-detail-modal';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { X, ListChecks, Activity, DollarSign, ArrowUpRight, ArrowDownRight, Timer, RotateCw, Rows3, Columns3, Layers, List, Minimize2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { config } from '@/lib/config';
import type { KanbanTask, AgentToolCall } from '@/lib/store/kanban-store';

interface KanbanBoardProps {
  panelWidth?: number;
}

function formatTokenCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface ContextMetrics {
  totalTokens: number;
  contextWindow: number;
  percentage: number;
  colorClass: string;
}

function getContextMetrics(sessionUsage: { inputTokens?: number; outputTokens?: number; cacheReadInputTokens?: number }, defaultContextWindow = 200_000): ContextMetrics | null {
  const inputTokens = sessionUsage.inputTokens ?? 0;
  const outputTokens = sessionUsage.outputTokens ?? 0;
  const cacheReadInputTokens = sessionUsage.cacheReadInputTokens ?? 0;

  const totalTokens = inputTokens + outputTokens - cacheReadInputTokens;

  if (totalTokens <= 0) return null;

  const contextWindow = defaultContextWindow;
  const percentage = (totalTokens / contextWindow) * 100;

  let colorClass = 'bg-status-success';
  if (percentage >= 80) {
    colorClass = 'bg-status-error';
  } else if (percentage >= 50) {
    colorClass = 'bg-status-warning';
  }

  return {
    totalTokens,
    contextWindow,
    percentage,
    colorClass,
  };
}

function renderContextIndicator(
  metrics: ContextMetrics,
  isCompacting: boolean,
  onCompact: () => void
): React.ReactNode {
  const { totalTokens, contextWindow, percentage, colorClass } = metrics;

  return (
    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        <div className="h-1.5 flex-1 bg-muted rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-300", colorClass)}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
        <span className={cn("whitespace-nowrap font-medium", percentage >= 80 ? "text-status-error" : percentage >= 50 ? "text-status-warning" : "text-status-success")}>
          {formatTokenCount(totalTokens)}/{formatTokenCount(contextWindow)} ({percentage.toFixed(0)}%)
        </span>
      </div>
      <Button
        onClick={onCompact}
        disabled={isCompacting}
        size="sm"
        variant="ghost"
        className="h-5 px-1.5 gap-1 text-[10px] hover:bg-muted/60"
        title="Compact context to reduce token usage"
      >
        {isCompacting ? (
          <Loader2 className="h-2.5 w-2.5 animate-spin" />
        ) : (
          <Minimize2 className="h-2.5 w-2.5" />
        )}
        <span className="hidden sm:inline">Compact</span>
      </Button>
    </div>
  );
}

export function KanbanBoard({ panelWidth = 320 }: KanbanBoardProps) {
  const isNarrow = panelWidth < config.kanban.breakpoints.narrow;
  const isCompact = panelWidth < config.kanban.breakpoints.compact;

  const tasks = useKanbanStore((s) => s.tasks);
  const toolCalls = useKanbanStore((s) => s.toolCalls);
  const activeTab = useKanbanStore((s) => s.activeTab);
  const setActiveTab = useKanbanStore((s) => s.setActiveTab);
  const taskLayout = useKanbanStore((s) => s.taskLayout);
  const setTaskLayout = useKanbanStore((s) => s.setTaskLayout);
  const setOpen = useKanbanStore((s) => s.setOpen);
  const sessionUsage = useKanbanStore((s) => s.sessionUsage);

  const isCompacting = useChatStore((s) => s.isCompacting);
  const { sendCompact } = useWebSocket();

  const [selectedTask, setSelectedTask] = useState<KanbanTask | null>(null);
  const [selectedToolCall, setSelectedToolCall] = useState<AgentToolCall | null>(null);
  const [activityViewMode, setActivityViewMode] = useState<ActivityViewMode>('grouped');

  const handleCompact = () => {
    if (!isCompacting) {
      sendCompact();
    }
  };

  const pendingTasks = tasks.filter((t) => t.status === 'pending');
  const inProgressTasks = tasks.filter((t) => t.status === 'in_progress');
  const completedTasks = tasks.filter((t) => t.status === 'completed');

  const activeCount = inProgressTasks.length;

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="flex h-10 items-center justify-between border-b px-3 shrink-0">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold text-foreground">Task Board</h2>
          {activeCount > 0 && (
            <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-status-info/10 text-status-info border border-status-info/20 animate-pulse">
              {activeCount} active
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => setOpen(false)}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Usage Summary */}
      {sessionUsage && (
        <div className="px-3 py-1.5 border-b bg-muted/30 shrink-0">
          <div className={cn("flex items-center flex-wrap text-[10px] text-muted-foreground", isNarrow ? "gap-x-2 gap-y-0.5" : "gap-3")}>
            {sessionUsage.isError && (
              <span className="h-2 w-2 rounded-full bg-red-500 shrink-0" />
            )}
            <span className="inline-flex items-center gap-1">
              <DollarSign className="h-3 w-3" />
              {sessionUsage.totalCostUsd.toFixed(4)}
            </span>
            {sessionUsage.inputTokens !== undefined && (
              <span className="inline-flex items-center gap-1">
                <ArrowUpRight className="h-3 w-3" />
                {formatTokenCount(sessionUsage.inputTokens)}
              </span>
            )}
            {sessionUsage.outputTokens !== undefined && (
              <span className="inline-flex items-center gap-1">
                <ArrowDownRight className="h-3 w-3" />
                {formatTokenCount(sessionUsage.outputTokens)}
              </span>
            )}
            <span className="inline-flex items-center gap-1">
              <Timer className="h-3 w-3" />
              {(sessionUsage.durationMs / 1000).toFixed(1)}s
            </span>
            <span className="inline-flex items-center gap-1">
              <RotateCw className="h-3 w-3" />
              {sessionUsage.turnCount} turns
            </span>
          </div>
          {/* Context Window Indicator */}
          {(() => {
            const metrics = getContextMetrics(sessionUsage);
            return metrics ? (
              <div className="mt-1.5 pt-1.5 border-t border-muted/50">
                {renderContextIndicator(metrics, isCompacting, handleCompact)}
              </div>
            ) : null;
          })()}
        </div>
      )}

      {/* Tabs */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as 'tasks' | 'activity')}
          className="flex-1 flex flex-col overflow-hidden"
        >
          <div className={cn("pt-2 shrink-0 flex items-center gap-2", isNarrow ? "px-2" : "px-3")}>
            <TabsList className="flex-1 h-8">
              <TabsTrigger value="tasks" className="flex-1 text-xs h-6 gap-1.5">
                <ListChecks className="h-3 w-3" />
                Tasks
                {tasks.length > 0 && (
                  <span className="text-[10px] text-muted-foreground">
                    ({tasks.length})
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="activity" className="flex-1 text-xs h-6 gap-1.5">
                <Activity className="h-3 w-3" />
                Activity
                {toolCalls.length > 0 && (
                  <span className="text-[10px] text-muted-foreground">
                    ({toolCalls.length})
                  </span>
                )}
              </TabsTrigger>
            </TabsList>
            {activeTab === 'tasks' && !isCompact && (
              <div className="flex items-center border rounded-md h-8">
                <button
                  type="button"
                  onClick={() => setTaskLayout('stack')}
                  className={cn(
                    'h-full px-1.5 rounded-l-md transition-colors',
                    taskLayout === 'stack' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                  title="Stack layout"
                >
                  <Rows3 className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setTaskLayout('columns')}
                  className={cn(
                    'h-full px-1.5 rounded-r-md transition-colors',
                    taskLayout === 'columns' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                  title="Column layout"
                >
                  <Columns3 className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
            {activeTab === 'activity' && (
              <div className="flex items-center border rounded-md h-8">
                <button
                  type="button"
                  onClick={() => setActivityViewMode('grouped')}
                  className={cn(
                    'h-full px-1.5 rounded-l-md transition-colors',
                    activityViewMode === 'grouped' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                  title="Group by agent"
                >
                  <Layers className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setActivityViewMode('timeline')}
                  className={cn(
                    'h-full px-1.5 rounded-r-md transition-colors',
                    activityViewMode === 'timeline' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                  title="Timeline view"
                >
                  <List className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>

          <TabsContent value="tasks" className="mt-0 flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              {(taskLayout === 'stack' || isCompact) ? (
                <div className="space-y-2 px-3 pt-2 pb-4">
                  <KanbanColumn title="In Progress" status="in_progress" tasks={inProgressTasks} onSelectTask={setSelectedTask} />
                  <KanbanColumn title="Pending" status="pending" tasks={pendingTasks} onSelectTask={setSelectedTask} />
                  <KanbanColumn title="Completed" status="completed" tasks={completedTasks} onSelectTask={setSelectedTask} />
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-1 px-1 pt-2 pb-4 h-full">
                  <div className="flex flex-col min-h-0">
                    <KanbanColumn title="Pending" status="pending" tasks={pendingTasks} onSelectTask={setSelectedTask} defaultExpanded />
                  </div>
                  <div className="flex flex-col min-h-0">
                    <KanbanColumn title="In Progress" status="in_progress" tasks={inProgressTasks} onSelectTask={setSelectedTask} defaultExpanded />
                  </div>
                  <div className="flex flex-col min-h-0">
                    <KanbanColumn title="Done" status="completed" tasks={completedTasks} onSelectTask={setSelectedTask} defaultExpanded />
                  </div>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="activity" className="mt-0 flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="px-2">
                <AgentActivity onSelectToolCall={setSelectedToolCall} panelWidth={panelWidth} viewMode={activityViewMode} />
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>

      {/* Detail Modal */}
      <KanbanDetailModal
        task={selectedTask}
        toolCall={selectedToolCall}
        onClose={() => { setSelectedTask(null); setSelectedToolCall(null); }}
      />
    </div>
  );
}
