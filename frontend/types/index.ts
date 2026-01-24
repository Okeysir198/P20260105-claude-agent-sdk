// types/index.ts
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// Question types for AskUserQuestion prompts
export interface QuestionOption {
  value: string;
  description?: string;
}

export interface Question {
  question: string;
  options: QuestionOption[];
  allowMultiple?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool_use' | 'tool_result';
  content: string;
  timestamp: Date;
  toolName?: string;
  toolInput?: Record<string, any>;
  toolUseId?: string;
  isError?: boolean;
}

export interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
}

export interface Agent {
  agent_id: string;
  name: string;
  description: string;
  model: string;
  is_default: boolean;
}

export interface Session {
  session_id: string;
  first_message: string | null;
  created_at: string;
  turn_count: number;
  user_id: string | null;
}

// Re-export API types
export * from './api';
export * from './websocket';
