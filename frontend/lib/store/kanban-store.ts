import { create } from 'zustand';
import type { ChatMessage } from '@/types';
import { getToolSummary } from '@/lib/tool-config';

// === Types ===

export interface KanbanTask {
  id: string;
  subject: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  activeForm?: string;
  owner?: string;
  source: 'TaskCreate' | 'TodoWrite' | 'Task';
  messageId: string;
}

export interface AgentToolCall {
  id: string;
  toolName: string;
  summary: string;
  agent: string;
  timestamp: Date;
  status: 'running' | 'completed' | 'error';
}

export interface SubagentInfo {
  type: string;
  description: string;
  taskToolUseId: string;
  status: 'running' | 'completed';
}

interface KanbanState {
  isOpen: boolean;
  activeTab: 'tasks' | 'activity';
  tasks: KanbanTask[];
  toolCalls: AgentToolCall[];
  subagents: SubagentInfo[];

  setOpen: (open: boolean) => void;
  toggleOpen: () => void;
  setActiveTab: (tab: 'tasks' | 'activity') => void;
  syncFromMessages: (messages: ChatMessage[]) => void;
  reset: () => void;
}

// === Helper Functions ===

function getActiveSubagent(
  subagents: SubagentInfo[],
  completedToolUseIds: Set<string>
): string {
  // Find the most recently started subagent that hasn't completed
  for (let i = subagents.length - 1; i >= 0; i--) {
    if (!completedToolUseIds.has(subagents[i].taskToolUseId)) {
      return subagents[i].type;
    }
  }
  return 'main';
}

// === Store ===

export const useKanbanStore = create<KanbanState>()((set) => ({
  isOpen: false,
  activeTab: 'tasks',
  tasks: [],
  toolCalls: [],
  subagents: [],

  setOpen: (open) => set({ isOpen: open }),
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  reset: () => set({ tasks: [], toolCalls: [], subagents: [] }),

  syncFromMessages: (messages: ChatMessage[]) => {
    const tasks: KanbanTask[] = [];
    const toolCalls: AgentToolCall[] = [];
    const subagents: SubagentInfo[] = [];
    const taskMap = new Map<string, KanbanTask>();
    const completedToolUseIds = new Set<string>();

    // First pass: identify completed subagents (tool_result messages with toolUseId matching a Task tool_use)
    const taskToolUseIds = new Set<string>();

    for (const msg of messages) {
      if (msg.role === 'tool_use' && msg.toolName === 'Task') {
        taskToolUseIds.add(msg.id);
      }
      if (msg.role === 'tool_result' && msg.toolUseId && taskToolUseIds.has(msg.toolUseId)) {
        completedToolUseIds.add(msg.toolUseId);
      }
    }

    // Second pass: build state
    for (const msg of messages) {
      // --- TaskCreate ---
      if (msg.role === 'tool_use' && msg.toolName === 'TaskCreate') {
        const input = msg.toolInput;
        if (input) {
          const task: KanbanTask = {
            id: (input.taskId as string) || msg.id,
            subject: (input.subject as string) || 'Untitled task',
            description: (input.description as string) || '',
            status: 'pending',
            activeForm: input.activeForm as string | undefined,
            owner: getActiveSubagent(subagents, completedToolUseIds),
            source: 'TaskCreate',
            messageId: msg.id,
          };
          tasks.push(task);
          taskMap.set(task.id, task);
        }
      }

      // --- TaskUpdate ---
      if (msg.role === 'tool_use' && msg.toolName === 'TaskUpdate') {
        const input = msg.toolInput;
        if (input?.taskId) {
          const taskId = input.taskId as string;
          const existing = taskMap.get(taskId);
          if (existing) {
            if (input.status) existing.status = input.status as KanbanTask['status'];
            if (input.subject) existing.subject = input.subject as string;
            if (input.description) existing.description = input.description as string;
            if (input.activeForm) existing.activeForm = input.activeForm as string;
            if (input.owner) existing.owner = input.owner as string;
          }
        }
      }

      // --- TaskList / TaskGet result handling ---
      // TaskList tool_result contains task data we can use to create/update tasks
      if (msg.role === 'tool_result' && msg.toolUseId) {
        // Find the corresponding tool_use to check if it was TaskList
        const toolUseMsg = messages.find(
          (m) => m.role === 'tool_use' && m.id === msg.toolUseId
        );
        if (toolUseMsg?.toolName === 'TaskList' && typeof msg.content === 'string' && msg.content.trim()) {
          try {
            // TaskList result is a text summary; try to parse structured data if JSON
            const parsed = JSON.parse(msg.content);
            if (Array.isArray(parsed)) {
              for (const item of parsed) {
                const id = String(item.id || item.taskId || '');
                if (id && !taskMap.has(id)) {
                  const task: KanbanTask = {
                    id,
                    subject: (item.subject || item.title || 'Task') as string,
                    description: (item.description || '') as string,
                    status: (['pending', 'in_progress', 'completed'].includes(item.status)
                      ? item.status : 'pending') as KanbanTask['status'],
                    owner: (item.owner || 'main') as string,
                    source: 'TaskCreate',
                    messageId: msg.id,
                  };
                  tasks.push(task);
                  taskMap.set(task.id, task);
                }
              }
            }
          } catch {
            // TaskList result is not JSON - that's fine, tasks were already created via TaskCreate
          }
        }
      }

      // --- TodoWrite ---
      if (msg.role === 'tool_use' && msg.toolName === 'TodoWrite') {
        const input = msg.toolInput;
        const todos = input?.todos as Array<Record<string, unknown>> | undefined;

        if (todos && Array.isArray(todos)) {
          // Clear previous TodoWrite tasks and replace with new ones
          const nonTodoTasks = tasks.filter((t) => t.source !== 'TodoWrite');
          tasks.length = 0;
          tasks.push(...nonTodoTasks);

          // Re-populate taskMap
          taskMap.clear();
          for (const t of tasks) taskMap.set(t.id, t);

          todos.forEach((todo, idx) => {
            const subject = (todo.subject || todo.content || todo.title || todo.description || 'Untitled') as string;
            const description = (todo.description || todo.content || '') as string;
            const status = (todo.status as string) || 'pending';
            const task: KanbanTask = {
              id: `todo-${idx}`,
              subject,
              description,
              status: (['pending', 'in_progress', 'completed'].includes(status)
                ? status : 'pending') as KanbanTask['status'],
              activeForm: (todo.activeForm as string) || undefined,
              owner: getActiveSubagent(subagents, completedToolUseIds),
              source: 'TodoWrite',
              messageId: msg.id,
            };
            tasks.push(task);
            taskMap.set(task.id, task);
          });
        }
      }

      // --- Task (subagent delegation) → also create a kanban task ---
      if (msg.role === 'tool_use' && msg.toolName === 'Task') {
        const input = msg.toolInput;
        if (input?.subagent_type) {
          const subagentType = input.subagent_type as string;
          const desc = (input.description as string) || (input.prompt as string) || '';
          const isCompleted = completedToolUseIds.has(msg.id);

          subagents.push({
            type: subagentType,
            description: desc,
            taskToolUseId: msg.id,
            status: isCompleted ? 'completed' : 'running',
          });

          // Create a kanban task card for this subagent delegation
          const task: KanbanTask = {
            id: `task-${msg.id}`,
            subject: desc || `${subagentType} subagent`,
            description: (input.prompt as string) || desc,
            status: isCompleted ? 'completed' : 'in_progress',
            activeForm: desc,
            owner: subagentType,
            source: 'Task',
            messageId: msg.id,
          };
          tasks.push(task);
          taskMap.set(task.id, task);
        }
      }

      // --- All tool_use messages → tool call timeline ---
      if (msg.role === 'tool_use' && msg.toolName) {
        const agent = getActiveSubagent(subagents, completedToolUseIds);

        // Check if this tool_use has a corresponding tool_result
        const hasResult = messages.some(
          (m) => m.role === 'tool_result' && m.toolUseId === msg.id
        );
        const isError = messages.some(
          (m) => m.role === 'tool_result' && m.toolUseId === msg.id && m.isError
        );

        toolCalls.push({
          id: msg.id,
          toolName: msg.toolName,
          summary: getToolSummary(msg.toolName, msg.toolInput) || '',
          agent,
          timestamp: msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp),
          status: isError ? 'error' : hasResult ? 'completed' : 'running',
        });
      }

      // --- tool_result for Task tool → mark subagent completed ---
      if (msg.role === 'tool_result' && msg.toolUseId) {
        // Already tracked in completedToolUseIds
      }
    }

    set({ tasks: [...tasks], toolCalls: [...toolCalls], subagents: [...subagents] });
  },
}));
