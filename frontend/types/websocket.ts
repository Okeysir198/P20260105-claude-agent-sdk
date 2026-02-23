import type { ContentBlock } from './index';

export interface WebSocketBaseEvent {
  type: string;
}

export interface QuestionOption {
  label: string;
  description: string;
}

export interface Question {
  header: string;
  question: string;
  options: QuestionOption[];
  multiSelect: boolean;
}

export interface AskUserQuestionEvent extends WebSocketBaseEvent {
  type: 'ask_user_question';
  question_id: string;
  questions: Question[];
  timeout: number;
}

export interface PlanStep {
  description: string;
  status?: 'pending' | 'in_progress' | 'completed';
}

export interface PlanApprovalEvent extends WebSocketBaseEvent {
  type: 'plan_approval';
  plan_id: string;
  title: string;
  summary: string;
  steps: PlanStep[];
  timeout: number;
}

export interface UserAnswerMessage {
  type: 'user_answer';
  question_id: string;
  answers: Record<string, string | string[]>;
}

export interface PlanApprovalMessage {
  type: 'plan_approval_response';
  plan_id: string;
  approved: boolean;
  feedback?: string;
}

export interface CancelRequestMessage {
  type: 'cancel_request';
}

export interface CompactRequestMessage {
  type: 'compact_request';
}

export interface CompactStartedEvent extends WebSocketBaseEvent {
  type: 'compact_started';
}

export interface CompactCompletedEvent extends WebSocketBaseEvent {
  type: 'compact_completed';
  session_id: string;
}

export interface CancelledEvent extends WebSocketBaseEvent {
  type: 'cancelled';
}

export interface SessionIdEvent extends WebSocketBaseEvent {
  type: 'session_id';
  session_id: string;
}

export interface TextDeltaEvent extends WebSocketBaseEvent {
  type: 'text_delta';
  text: string;
  parent_tool_use_id?: string;
}

export interface AssistantTextEvent extends WebSocketBaseEvent {
  type: 'assistant_text';
  text: string;
}

export interface ToolUseEvent extends WebSocketBaseEvent {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, any>;
  parent_tool_use_id?: string;
}

export interface ToolResultEvent extends WebSocketBaseEvent {
  type: 'tool_result';
  tool_use_id: string;
  content: string;
  is_error?: boolean;
  parent_tool_use_id?: string;
}

export interface DoneEvent extends WebSocketBaseEvent {
  type: 'done';
  turn_count: number;
  total_cost_usd?: number;
  duration_ms?: number;
  duration_api_ms?: number;
  is_error?: boolean;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    cache_creation_input_tokens?: number;
    cache_read_input_tokens?: number;
    context_window?: number;
    [key: string]: unknown;
  };
}

export interface ErrorEvent extends WebSocketBaseEvent {
  type: 'error';
  error: string;
}

export interface ReadyEvent extends WebSocketBaseEvent {
  type: 'ready';
  session_id?: string;
  cwd_id?: string;
  resumed?: boolean;
  turn_count?: number;
}

export interface FileUploadedEvent extends WebSocketBaseEvent {
  type: 'file_uploaded';
  file: {
    safe_name: string;
    original_name: string;
    file_type: 'input' | 'output';
    size_bytes: number;
    content_type: string;
    created_at: string;
    session_id: string;
  };
}

export interface FileDeletedEvent extends WebSocketBaseEvent {
  type: 'file_deleted';
  safe_name: string;
  file_type: 'input' | 'output';
}

export interface ClientMessage {
  content: string | ContentBlock[];
}

export type WebSocketEvent =
  | SessionIdEvent
  | TextDeltaEvent
  | AssistantTextEvent
  | ToolUseEvent
  | ToolResultEvent
  | DoneEvent
  | ErrorEvent
  | ReadyEvent
  | AskUserQuestionEvent
  | PlanApprovalEvent
  | CancelledEvent
  | CompactStartedEvent
  | CompactCompletedEvent
  | FileUploadedEvent
  | FileDeletedEvent;
