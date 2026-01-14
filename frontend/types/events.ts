/**
 * SSE Event Types for Claude Agent SDK API
 * @module types/events
 */

export interface SessionIdEvent {
  session_id: string;
}

export interface TextDeltaEvent {
  text: string;
}

export interface ToolUseEvent {
  tool_name: string;
  input: Record<string, unknown>;
}

export interface ToolResultEvent {
  tool_use_id: string;
  content: string;
  is_error: boolean;
}

export interface DoneEvent {
  session_id: string;
  turn_count: number;
  total_cost_usd?: number;
}

export interface ErrorEvent {
  error: string;
}

export type SSEEventType =
  | 'session_id'
  | 'text_delta'
  | 'tool_use'
  | 'tool_result'
  | 'done'
  | 'error';

export type ParsedSSEEvent =
  | { type: 'session_id'; data: SessionIdEvent }
  | { type: 'text_delta'; data: TextDeltaEvent }
  | { type: 'tool_use'; data: ToolUseEvent }
  | { type: 'tool_result'; data: ToolResultEvent }
  | { type: 'done'; data: DoneEvent }
  | { type: 'error'; data: ErrorEvent };

export interface RawSSEEvent {
  event: SSEEventType;
  data: string;
}

const SSE_EVENT_TYPES: SSEEventType[] = [
  'session_id',
  'text_delta',
  'tool_use',
  'tool_result',
  'done',
  'error',
];

export function isSSEEventType(type: string): type is SSEEventType {
  return SSE_EVENT_TYPES.includes(type as SSEEventType);
}

export type SSEEventParser = (eventType: SSEEventType, data: string) => ParsedSSEEvent | null;
