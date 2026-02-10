'use client';

import { useState } from 'react';
import { useKanbanStore } from '@/lib/store/kanban-store';
import { KanbanColumn } from './kanban-column';
import { AgentActivity } from './agent-activity';
import { KanbanDetailModal } from './kanban-detail-modal';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { X, ListChecks, Activity } from 'lucide-react';
import type { KanbanTask, AgentToolCall } from '@/lib/store/kanban-store';

export function KanbanBoard() {
  const tasks = useKanbanStore((s) => s.tasks);
  const toolCalls = useKanbanStore((s) => s.toolCalls);
  const activeTab = useKanbanStore((s) => s.activeTab);
  const setActiveTab = useKanbanStore((s) => s.setActiveTab);
  const setOpen = useKanbanStore((s) => s.setOpen);

  const [selectedTask, setSelectedTask] = useState<KanbanTask | null>(null);
  const [selectedToolCall, setSelectedToolCall] = useState<AgentToolCall | null>(null);

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

      {/* Tabs */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as 'tasks' | 'activity')}
          className="flex-1 flex flex-col overflow-hidden"
        >
          <div className="px-3 pt-2 shrink-0">
            <TabsList className="w-full h-8">
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
          </div>

          <TabsContent value="tasks" className="mt-0 flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="space-y-2 px-3 pt-2 pb-4">
                <KanbanColumn title="In Progress" status="in_progress" tasks={inProgressTasks} onSelectTask={setSelectedTask} />
                <KanbanColumn title="Pending" status="pending" tasks={pendingTasks} onSelectTask={setSelectedTask} />
                <KanbanColumn title="Completed" status="completed" tasks={completedTasks} onSelectTask={setSelectedTask} />
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="activity" className="mt-0 flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="px-2">
                <AgentActivity onSelectToolCall={setSelectedToolCall} />
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
