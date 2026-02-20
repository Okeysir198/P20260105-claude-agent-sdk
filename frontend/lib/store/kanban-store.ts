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
  delegatedTo?: string;
  source: 'TaskCreate' | 'TodoWrite' | 'Task';
  messageId: string;
  toolInput?: Record<string, unknown>;
  timestamp?: Date;
}

export interface AgentToolCall {
  id: string;
  toolName: string;
  summary: string;
  agent: string;
  timestamp: Date;
  status: 'running' | 'completed' | 'error';
  toolInput?: Record<string, unknown>;
  resultContent?: string;
  parentToolUseId?: string;
}

export interface SubagentInfo {
  type: string;
  description: string;
  taskToolUseId: string;
  status: 'running' | 'completed';
}

export interface SessionUsage {
  totalCostUsd: number;
  durationMs: number;
  durationApiMs: number;
  turnCount: number;
  isError: boolean;
  inputTokens?: number;
  outputTokens?: number;
  cacheCreationInputTokens?: number;
  cacheReadInputTokens?: number;
  contextWindow?: number;
}

interface KanbanState {
  isOpen: boolean;
  activeTab: 'tasks' | 'activity';
  taskLayout: 'stack' | 'columns';
  tasks: KanbanTask[];
  toolCalls: AgentToolCall[];
  subagents: SubagentInfo[];
  sessionUsage: SessionUsage | null;

  setOpen: (open: boolean) => void;
  toggleOpen: () => void;
  setActiveTab: (tab: 'tasks' | 'activity') => void;
  setTaskLayout: (layout: 'stack' | 'columns') => void;
  setSessionUsage: (usage: SessionUsage | null) => void;
  syncFromMessages: (messages: ChatMessage[]) => void;
  reset: () => void;
}

// === Helper Functions ===

function parseTimestamp(ts: Date | string | undefined): Date {
  if (!ts) return new Date();
  return ts instanceof Date ? ts : new Date(ts);
}

/**
 * Find the most recently started subagent that hasn't completed,
 * or return 'main' if none is active.
 */
function getActiveSubagent(
  subagents: SubagentInfo[],
  completedToolUseIds: Set<string>
): string {
  for (let i = subagents.length - 1; i >= 0; i--) {
    if (!completedToolUseIds.has(subagents[i].taskToolUseId)) {
      return subagents[i].type;
    }
  }
  return 'main';
}

/**
 * Resolve which agent owns a message, using parentToolUseId for explicit
 * attribution or falling back to the currently active subagent.
 */
function resolveAgent(
  parentToolUseId: string | undefined,
  subagents: SubagentInfo[],
  completedToolUseIds: Set<string>
): string {
  if (parentToolUseId) {
    const parent = subagents.find(s => s.taskToolUseId === parentToolUseId);
    if (parent) return parent.type;
  }
  return getActiveSubagent(subagents, completedToolUseIds);
}

function extractKeywords(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9_.\-]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter((w) => w.length >= 3);
}

/**
 * Fuzzy match two task subjects by checking keyword overlap.
 * Returns true if at least half of the shorter subject's keywords appear
 * in the longer subject.
 */
function fuzzySubjectMatch(a: string, b: string): boolean {
  const wordsA = extractKeywords(a);
  const wordsB = extractKeywords(b);
  if (wordsA.length === 0 || wordsB.length === 0) return false;

  const shorter = wordsA.length <= wordsB.length ? wordsA : wordsB;
  const longerStr = (wordsA.length <= wordsB.length ? wordsB : wordsA).join(' ');

  let matchCount = 0;
  for (const word of shorter) {
    if (longerStr.includes(word)) matchCount++;
  }

  return matchCount / shorter.length >= 0.5;
}

// === Store ===

export const useKanbanStore = create<KanbanState>()((set) => ({
  isOpen: false,
  activeTab: 'tasks',
  taskLayout: 'columns',
  tasks: [],
  toolCalls: [],
  subagents: [],
  sessionUsage: null,

  setOpen: (open) => set({ isOpen: open }),
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setTaskLayout: (layout) => set({ taskLayout: layout }),
  setSessionUsage: (usage) => set({ sessionUsage: usage }),
  reset: () => set({ tasks: [], toolCalls: [], subagents: [], sessionUsage: null }),

  syncFromMessages: (messages: ChatMessage[]) => {
    const tasks: KanbanTask[] = [];
    const toolCalls: AgentToolCall[] = [];
    const subagents: SubagentInfo[] = [];
    const taskMap = new Map<string, KanbanTask>();
    const completedToolUseIds = new Set<string>();
    const pendingDelegations: Array<{
      subagentType: string;
      desc: string;
      canonicalId: string;
      isCompleted: boolean;
      messageId: string;
      toolInput?: Record<string, unknown>;
      timestamp?: Date;
    }> = [];

    // First pass: identify completed subagents (tool_result messages with toolUseId matching a Task tool_use)
    const taskToolUseIds = new Set<string>();

    for (const msg of messages) {
      if (msg.role === 'tool_use' && msg.toolName === 'Task') {
        // Use toolUseId (from history) or id (from live streaming) as the canonical ID
        taskToolUseIds.add(msg.toolUseId || msg.id);
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
            owner: resolveAgent(msg.parentToolUseId, subagents, completedToolUseIds),
            source: 'TaskCreate',
            messageId: msg.id,
            toolInput: msg.toolInput,
            timestamp: parseTimestamp(msg.timestamp),
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
                    timestamp: parseTimestamp(msg.timestamp),
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

          const todoOwner = resolveAgent(msg.parentToolUseId, subagents, completedToolUseIds);

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
              owner: todoOwner,
              source: 'TodoWrite',
              messageId: msg.id,
              toolInput: msg.toolInput,
              timestamp: parseTimestamp(msg.timestamp),
            };
            tasks.push(task);
            taskMap.set(task.id, task);
          });
        }
      }

      // --- Task (subagent delegation) → collect for dedup after loop ---
      if (msg.role === 'tool_use' && msg.toolName === 'Task') {
        const input = msg.toolInput;
        if (input?.subagent_type) {
          const subagentType = input.subagent_type as string;
          const desc = (input.description as string) || (input.prompt as string) || '';
          // Use toolUseId (from history) or id (from live streaming) for completion check
          const canonicalId = msg.toolUseId || msg.id;
          const isCompleted = completedToolUseIds.has(canonicalId);

          subagents.push({
            type: subagentType,
            description: desc,
            taskToolUseId: canonicalId,
            status: isCompleted ? 'completed' : 'running',
          });

          // Defer card creation — collected for dedup pass after the loop
          pendingDelegations.push({
            subagentType,
            desc,
            canonicalId,
            isCompleted,
            messageId: msg.id,
            toolInput: msg.toolInput,
            timestamp: parseTimestamp(msg.timestamp),
          });
        }
      }

      // --- All tool_use messages → tool call timeline ---
      if (msg.role === 'tool_use' && msg.toolName) {
        const agent = resolveAgent(msg.parentToolUseId, subagents, completedToolUseIds);

        // Check if this tool_use has a corresponding tool_result
        const toolId = msg.toolUseId || msg.id;
        const resultMsg = messages.find(
          (m) => m.role === 'tool_result' && m.toolUseId === toolId
        );
        const hasResult = !!resultMsg;
        const isError = hasResult && !!resultMsg.isError;

        // Extract result content as string
        let resultContent: string | undefined;
        if (resultMsg) {
          resultContent = typeof resultMsg.content === 'string'
            ? resultMsg.content
            : Array.isArray(resultMsg.content)
              ? JSON.stringify(resultMsg.content)
              : undefined;
        }

        toolCalls.push({
          id: msg.id,
          toolName: msg.toolName,
          summary: getToolSummary(msg.toolName, msg.toolInput) || '',
          agent,
          timestamp: parseTimestamp(msg.timestamp),
          status: isError ? 'error' : hasResult ? 'completed' : 'running',
          toolInput: msg.toolInput,
          resultContent,
          parentToolUseId: msg.parentToolUseId,
        });
      }

      // --- Assistant text messages → activity timeline ---
      if (msg.role === 'assistant' && typeof msg.content === 'string' && msg.content.trim()) {
        const agent = resolveAgent(msg.parentToolUseId, subagents, completedToolUseIds);

        // Truncate long text for summary
        const text = msg.content.trim();
        const summary = text.length > 120 ? text.slice(0, 117) + '...' : text;

        toolCalls.push({
          id: msg.id,
          toolName: '__text__',
          summary,
          agent,
          timestamp: parseTimestamp(msg.timestamp),
          status: 'completed',
          toolInput: undefined,
          resultContent: text,
          parentToolUseId: msg.parentToolUseId,
        });
      }

    }

    // --- Dedup pass: enrich TaskCreate/TodoWrite tasks or create standalone Task cards ---
    const matchedTaskIds = new Set<string>();

    for (const d of pendingDelegations) {
      // Try to find a matching TaskCreate/TodoWrite task:
      // 1. Match by owner (subagent type)
      // 2. If no owner match, try fuzzy subject matching
      let matchingTask = tasks.find(
        (t) =>
          (t.source === 'TaskCreate' || t.source === 'TodoWrite') &&
          !matchedTaskIds.has(t.id) &&
          t.owner === d.subagentType
      );

      if (!matchingTask && d.desc) {
        matchingTask = tasks.find(
          (t) =>
            (t.source === 'TaskCreate' || t.source === 'TodoWrite') &&
            !matchedTaskIds.has(t.id) &&
            fuzzySubjectMatch(t.subject, d.desc)
        );
      }

      if (matchingTask) {
        // Enrich existing task with delegation info (dedup — no new card)
        matchingTask.delegatedTo = d.subagentType;
        matchedTaskIds.add(matchingTask.id);

        // Propagate status from delegation
        if (d.isCompleted) {
          matchingTask.status = 'completed';
        } else if (matchingTask.status === 'pending') {
          matchingTask.status = 'in_progress';
        }
      } else {
        // Standalone delegation — create a Task card as fallback
        const task: KanbanTask = {
          id: `task-${d.canonicalId}`,
          subject: d.desc || `${d.subagentType} subagent`,
          description: d.desc,
          status: d.isCompleted ? 'completed' : 'in_progress',
          activeForm: d.desc,
          owner: d.subagentType,
          source: 'Task',
          messageId: d.messageId,
          toolInput: d.toolInput,
          timestamp: d.timestamp,
        };
        tasks.push(task);
        taskMap.set(task.id, task);
      }
    }

    set({ tasks: [...tasks], toolCalls: [...toolCalls], subagents: [...subagents] });
  },
}));
