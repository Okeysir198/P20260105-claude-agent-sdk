import {
  Terminal,
  FileText,
  FileEdit,
  Search,
  Globe,
  FolderTree,
  MessageSquare,
  Wrench,
  CheckSquare,
  ClipboardList,
  CheckCircle,
  ListPlus,
  ListChecks,
  List,
  ListTodo,
  Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * Tool configuration for consistent styling across the application.
 * Uses CSS custom properties defined in globals.css for theming.
 */

export type ToolName =
  | 'Bash'
  | 'Read'
  | 'Write'
  | 'Edit'
  | 'Grep'
  | 'Glob'
  | 'WebFetch'
  | 'WebSearch'
  | 'Task'
  | 'AskUserQuestion'
  | 'TodoWrite'
  | 'EnterPlanMode'
  | 'ExitPlanMode'
  | 'TaskCreate'
  | 'TaskUpdate'
  | 'TaskList'
  | 'TaskGet'
  | 'Skill';

interface ToolConfig {
  icon: LucideIcon;
  colorVar: string;
}

/**
 * Tool configuration mapping tool names to their icons and color CSS variables.
 */
export const TOOL_CONFIG: Record<ToolName, ToolConfig> = {
  Bash: { icon: Terminal, colorVar: '--tool-bash' },
  Read: { icon: FileText, colorVar: '--tool-read' },
  Write: { icon: FileEdit, colorVar: '--tool-write' },
  Edit: { icon: FileEdit, colorVar: '--tool-write' },
  Grep: { icon: Search, colorVar: '--tool-search' },
  Glob: { icon: Search, colorVar: '--tool-search' },
  WebFetch: { icon: Globe, colorVar: '--tool-web' },
  WebSearch: { icon: Globe, colorVar: '--tool-web' },
  Task: { icon: FolderTree, colorVar: '--tool-task' },
  AskUserQuestion: { icon: MessageSquare, colorVar: '--tool-question' },
  TodoWrite: { icon: CheckSquare, colorVar: '--tool-write' },
  EnterPlanMode: { icon: ClipboardList, colorVar: '--tool-plan' },
  ExitPlanMode: { icon: CheckCircle, colorVar: '--tool-plan' },
  TaskCreate: { icon: ListPlus, colorVar: '--tool-task' },
  TaskUpdate: { icon: ListChecks, colorVar: '--tool-task' },
  TaskList: { icon: List, colorVar: '--tool-task' },
  TaskGet: { icon: ListTodo, colorVar: '--tool-task' },
  Skill: { icon: Zap, colorVar: '--tool-mcp' },
};

const DEFAULT_TOOL_CONFIG: ToolConfig = {
  icon: Wrench,
  colorVar: '--tool-default',
};

/**
 * Get tool configuration by name.
 */
export function getToolConfig(toolName?: string): ToolConfig {
  if (!toolName) return DEFAULT_TOOL_CONFIG;
  return TOOL_CONFIG[toolName as ToolName] || DEFAULT_TOOL_CONFIG;
}

/**
 * Get the icon component for a tool.
 */
export function getToolIcon(toolName?: string): LucideIcon {
  return getToolConfig(toolName).icon;
}

/**
 * Get inline styles for tool-based coloring using CSS variables.
 */
export function getToolColorStyles(toolName?: string): {
  iconBg: React.CSSProperties;
  iconText: React.CSSProperties;
  border: React.CSSProperties;
  badge: React.CSSProperties;
} {
  const config = getToolConfig(toolName);
  const colorVar = config.colorVar;

  return {
    iconBg: {
      backgroundColor: `hsl(${cssVar(colorVar)} / 0.1)`,
    },
    iconText: {
      color: `hsl(${cssVar(colorVar)})`,
    },
    border: {
      borderLeftColor: `hsl(${cssVar(colorVar)})`,
    },
    badge: {
      backgroundColor: `hsl(${cssVar(colorVar)} / 0.1)`,
      color: `hsl(${cssVar(colorVar)})`,
    },
  };
}

/**
 * Helper to reference a CSS variable value.
 */
function cssVar(name: string): string {
  return `var(${name})`;
}

/**
 * Generate a smart summary based on tool type and input.
 */
export function getToolSummary(
  toolName?: string,
  input?: Record<string, unknown>
): string {
  if (!toolName || !input) return '';

  const summaryExtractors: Record<string, (input: Record<string, unknown>) => string> = {
    Bash: (i) => {
      const command = i.command as string | undefined;
      if (!command) return '';
      const cleaned = command.replace(/\s+/g, ' ').trim();
      return cleaned.length > 60 ? cleaned.slice(0, 57) + '...' : cleaned;
    },
    Read: (i) => {
      const filePath = i.file_path as string | undefined;
      if (!filePath) return '';
      const parts = filePath.split('/');
      return parts[parts.length - 1] || filePath;
    },
    Write: (i) => {
      const filePath = i.file_path as string | undefined;
      if (!filePath) return '';
      const parts = filePath.split('/');
      return parts[parts.length - 1] || filePath;
    },
    Edit: (i) => {
      const filePath = i.file_path as string | undefined;
      if (!filePath) return '';
      const parts = filePath.split('/');
      return parts[parts.length - 1] || filePath;
    },
    Grep: (i) => {
      const pattern = i.pattern as string | undefined;
      const path = i.path as string | undefined;
      if (!pattern) return '';
      const truncatedPattern =
        pattern.length > 30 ? pattern.slice(0, 27) + '...' : pattern;
      return `"${truncatedPattern}"${path ? ` in ${path}` : ''}`;
    },
    Glob: (i) => (i.pattern as string) || '',
    WebFetch: (i) => {
      const url = i.url as string | undefined;
      const query = i.query as string | undefined;
      if (url) {
        try {
          return new URL(url).hostname;
        } catch {
          return url.slice(0, 40);
        }
      }
      if (query) {
        return query.length > 40 ? query.slice(0, 37) + '...' : query;
      }
      return '';
    },
    WebSearch: (i) => {
      const url = i.url as string | undefined;
      const query = i.query as string | undefined;
      if (url) {
        try {
          return new URL(url).hostname;
        } catch {
          return url.slice(0, 40);
        }
      }
      if (query) {
        return query.length > 40 ? query.slice(0, 37) + '...' : query;
      }
      return '';
    },
    Task: (i) => {
      const description = i.description as string | undefined;
      if (!description) return '';
      return description.length > 50
        ? description.slice(0, 47) + '...'
        : description;
    },
    AskUserQuestion: (i) => {
      const questions = i.questions as Array<{ question: string }> | undefined;
      if (!questions || questions.length === 0) return '';
      const count = questions.length;
      return `${count} question${count > 1 ? 's' : ''}`;
    },
    TodoWrite: (i) => {
      const todos = i.todos as Array<{ content: string }> | undefined;
      if (!todos || todos.length === 0) return '';
      const count = todos.length;
      return `${count} todo${count > 1 ? 's' : ''}`;
    },
    EnterPlanMode: () => 'Planning mode',
    ExitPlanMode: () => 'Plan ready for approval',
    TaskCreate: (i) => (i.subject as string) || '',
    TaskUpdate: (i) => {
      const taskId = i.taskId as string | undefined;
      const status = i.status as string | undefined;
      if (taskId && status) return `#${taskId} → ${status}`;
      if (taskId) return `#${taskId}`;
      return '';
    },
    TaskList: () => 'List all tasks',
    TaskGet: (i) => {
      const taskId = i.taskId as string | undefined;
      return taskId ? `#${taskId}` : '';
    },
    Skill: (i) => {
      const skill = i.skill as string | undefined;
      return skill || '';
    },
  };

  const extractor = summaryExtractors[toolName];
  return extractor ? extractor(input) : '';
}
