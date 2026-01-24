// types/websocket.ts
export type EventType = 'session_id' | 'text_delta' | 'tool_use' | 'tool_result' | 'done' | 'error' | 'ready' | 'ask_user_question';

export interface WebSocketBaseEvent {
  type: EventType;
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

export interface UserAnswerMessage {
  type: 'user_answer';
  question_id: string;
  answers: Record<string, string | string[]>;  // question text -> selected label(s)
}

export interface SessionIdEvent extends WebSocketBaseEvent {
  type: 'session_id';
  session_id: string;
}

export interface TextDeltaEvent extends WebSocketBaseEvent {
  type: 'text_delta';
  text: string;
}

export interface ToolUseEvent extends WebSocketBaseEvent {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, any>;
}

export interface ToolResultEvent extends WebSocketBaseEvent {
  type: 'tool_result';
  tool_use_id: string;
  content: string;
  is_error?: boolean;
}

export interface DoneEvent extends WebSocketBaseEvent {
  type: 'done';
  turn_count: number;
  total_cost_usd?: number;
}

export interface ErrorEvent extends WebSocketBaseEvent {
  type: 'error';
  error: string;
}

export interface ReadyEvent extends WebSocketBaseEvent {
  type: 'ready';
  session_id?: string;
  resumed?: boolean;
  turn_count?: number;
}

export interface ClientMessage {
  content: string;
}

export type WebSocketEvent = SessionIdEvent | TextDeltaEvent | ToolUseEvent | ToolResultEvent | DoneEvent | ErrorEvent | ReadyEvent | AskUserQuestionEvent;
