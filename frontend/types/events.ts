/**
 * SSE Event Types for Claude Agent SDK API
 *
 * These types define the structure of Server-Sent Events (SSE) emitted
 * by the Claude Agent SDK API during streaming conversations.
 *
 * @module types/events
 */

/**
 * Event emitted at the start of a conversation with the session identifier.
 * This is typically the first event received when starting a new conversation.
 */
export interface SessionIdEvent {
  /** Unique identifier for the conversation session */
  session_id: string;
}

/**
 * Event emitted for each text chunk during streaming response.
 * Multiple text_delta events are emitted as the assistant generates content.
 */
export interface TextDeltaEvent {
  /** Incremental text content to append to the response */
  text: string;
}

/**
 * Event emitted when the assistant invokes a tool.
 * Contains the tool name and its input parameters.
 */
export interface ToolUseEvent {
  /** Name of the tool being invoked */
  tool_name: string;
  /** Input parameters passed to the tool */
  input: Record<string, unknown>;
}

/**
 * Event emitted when a tool execution completes.
 * Contains the result or error from the tool execution.
 */
export interface ToolResultEvent {
  /** Unique identifier linking this result to its tool_use event */
  tool_use_id: string;
  /** The output content from the tool execution */
  content: string;
  /** Whether the tool execution resulted in an error */
  is_error: boolean;
}

/**
 * Event emitted when the conversation turn completes.
 * Contains final statistics about the conversation.
 */
export interface DoneEvent {
  /** Session identifier for the completed conversation */
  session_id: string;
  /** Number of turns completed in this session */
  turn_count: number;
  /** Total cost in USD for API usage (optional) */
  total_cost_usd?: number;
}

/**
 * Event emitted when an error occurs during the conversation.
 * The connection may be closed after this event.
 */
export interface ErrorEvent {
  /** Error message describing what went wrong */
  error: string;
}

/**
 * String literal union of all possible SSE event types.
 * Used for type-safe event type checking.
 */
export type SSEEventType =
  | 'session_id'
  | 'text_delta'
  | 'tool_use'
  | 'tool_result'
  | 'done'
  | 'error';

/**
 * Discriminated union type for type-safe SSE event handling.
 *
 * This allows for exhaustive pattern matching when handling events:
 *
 * @example
 * ```typescript
 * function handleEvent(event: ParsedSSEEvent) {
 *   switch (event.type) {
 *     case 'session_id':
 *       console.log('Session started:', event.data.session_id);
 *       break;
 *     case 'text_delta':
 *       appendText(event.data.text);
 *       break;
 *     case 'tool_use':
 *       showToolExecution(event.data.tool_name, event.data.input);
 *       break;
 *     case 'tool_result':
 *       showToolResult(event.data.content, event.data.is_error);
 *       break;
 *     case 'done':
 *       finalizeConversation(event.data);
 *       break;
 *     case 'error':
 *       handleError(event.data.error);
 *       break;
 *   }
 * }
 * ```
 */
export type ParsedSSEEvent =
  | { type: 'session_id'; data: SessionIdEvent }
  | { type: 'text_delta'; data: TextDeltaEvent }
  | { type: 'tool_use'; data: ToolUseEvent }
  | { type: 'tool_result'; data: ToolResultEvent }
  | { type: 'done'; data: DoneEvent }
  | { type: 'error'; data: ErrorEvent };

/**
 * Raw SSE event structure before parsing.
 * Represents the structure of events as they arrive from the EventSource.
 */
export interface RawSSEEvent {
  /** The event type identifier */
  event: SSEEventType;
  /** JSON-encoded event data */
  data: string;
}

/**
 * Type guard to check if a string is a valid SSE event type.
 *
 * @param type - The string to check
 * @returns True if the string is a valid SSEEventType
 */
export function isSSEEventType(type: string): type is SSEEventType {
  return ['session_id', 'text_delta', 'tool_use', 'tool_result', 'done', 'error'].includes(type);
}

/**
 * Parser function type for converting raw SSE data to typed events.
 *
 * @param eventType - The type of the SSE event
 * @param data - The JSON string data from the event
 * @returns Parsed SSE event or null if parsing fails
 */
export type SSEEventParser = (eventType: SSEEventType, data: string) => ParsedSSEEvent | null;
