'use client';

import { useKanbanStore } from '@/lib/store/kanban-store';
import { KanbanColumn } from './kanban-column';
import { AgentActivity } from './agent-activity';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

export function KanbanBoard() {
  const tasks = useKanbanStore((s) => s.tasks);
  const activeTab = useKanbanStore((s) => s.activeTab);
  const setActiveTab = useKanbanStore((s) => s.setActiveTab);
  const setOpen = useKanbanStore((s) => s.setOpen);

  const pendingTasks = tasks.filter((t) => t.status === 'pending');
  const inProgressTasks = tasks.filter((t) => t.status === 'in_progress');
  const completedTasks = tasks.filter((t) => t.status === 'completed');

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="flex h-10 items-center justify-between border-b px-3 shrink-0">
        <h2 className="text-xs font-semibold text-foreground">Task Board</h2>
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
      <div className="px-3 pt-2">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'tasks' | 'activity')}>
          <TabsList className="w-full h-8">
            <TabsTrigger value="tasks" className="flex-1 text-xs h-6">
              Tasks
              {tasks.length > 0 && (
                <span className="ml-1.5 text-[10px] text-muted-foreground">
                  ({tasks.length})
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="activity" className="flex-1 text-xs h-6">
              Activity
            </TabsTrigger>
          </TabsList>

          <TabsContent value="tasks" className="mt-0">
            <ScrollArea className="h-[calc(100vh-7rem)]">
              {/* Desktop: 3 columns side by side */}
              <div className="hidden md:grid md:grid-cols-3 gap-1 pt-2 pb-4">
                <KanbanColumn title="Pending" status="pending" tasks={pendingTasks} />
                <KanbanColumn title="In Progress" status="in_progress" tasks={inProgressTasks} />
                <KanbanColumn title="Completed" status="completed" tasks={completedTasks} />
              </div>
              {/* Mobile: stacked columns */}
              <div className="md:hidden space-y-3 pt-2 pb-4">
                <KanbanColumn title="Pending" status="pending" tasks={pendingTasks} collapsible />
                <KanbanColumn title="In Progress" status="in_progress" tasks={inProgressTasks} collapsible />
                <KanbanColumn title="Completed" status="completed" tasks={completedTasks} collapsible />
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="activity" className="mt-0">
            <ScrollArea className="h-[calc(100vh-7rem)]">
              <AgentActivity />
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
