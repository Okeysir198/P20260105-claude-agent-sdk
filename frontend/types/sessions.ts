/**
 * Session Management Types for Claude Chat UI
 *
 * These types define the structure of session data, API requests,
 * and responses for managing conversation sessions.
 *
 * @module types/sessions
 */

/**
 * Information about a single conversation session.
 */
export interface SessionInfo {
  /** Unique identifier for the session */
  id: string;
  /** Timestamp when the session was created */
  created_at: string;
  /** Timestamp of the last activity in the session */
  last_activity: string;
  /** Number of turns completed in the session */
  turn_count: number;
  /** Total API cost in USD for this session (optional) */
  total_cost_usd?: number;
  /** Optional title or summary of the session */
  title?: string;
  /** First message or preview text from the session */
  preview?: string;
  /** Tags or labels associated with the session */
  tags?: string[];
  /** ID of the agent used in this session (optional) */
  agent_id?: string;
}

/**
 * Summary totals for session statistics.
 */
export interface SessionTotals {
  /** Total number of active sessions */
  active: number;
  /** Total number of sessions in history */
  history: number;
  /** Combined total of all sessions */
  total: number;
}

/**
 * Response structure for listing sessions.
 * Contains both active and historical sessions with totals.
 */
export interface SessionListResponse {
  /** Sessions that are currently active or recent */
  active_sessions: SessionInfo[];
  /** Sessions from conversation history */
  history_sessions: SessionInfo[];
  /** Summary totals for session counts */
  totals: SessionTotals;
}

/**
 * Request payload for creating a new conversation.
 */
export interface CreateConversationRequest {
  /** Initial message content to start the conversation */
  content: string;
  /** Optional session ID to resume an existing session */
  resume_session_id?: string;
  /** Optional agent ID to use a specific agent for the conversation */
  agent_id?: string;
  /** Optional array of skill names to enable for this conversation */
  skills?: string[];
  /** Optional system prompt override */
  system_prompt?: string;
}

/**
 * Request payload for sending a message in an existing conversation.
 */
export interface SendMessageRequest {
  /** Text content of the message to send */
  content: string;
}

/**
 * Request payload for resuming an existing session.
 */
export interface ResumeSessionRequest {
  /** ID of the session to resume */
  session_id: string;
  /** Optional new message to send when resuming */
  initial_message?: string;
}

/**
 * Response when creating or resuming a conversation.
 * Note: The actual response is an SSE stream, but this represents
 * any JSON metadata returned.
 */
export interface ConversationResponse {
  /** Session ID for the conversation */
  session_id: string;
  /** Conversation ID (may differ from session_id in some implementations) */
  conversation_id: string;
  /** Status of the operation */
  status: 'created' | 'resumed' | 'active';
}

/**
 * Request payload for interrupting an ongoing conversation.
 */
export interface InterruptRequest {
  /** Optional reason for the interruption */
  reason?: string;
}

/**
 * Response when interrupting a conversation.
 */
export interface InterruptResponse {
  /** Whether the interruption was successful */
  success: boolean;
  /** Session ID that was interrupted */
  session_id: string;
  /** Status message */
  message: string;
}

/**
 * Information about an available skill.
 */
export interface SkillInfo {
  /** Unique identifier/name of the skill */
  name: string;
  /** Human-readable description of the skill */
  description: string;
  /** Category or type of the skill */
  category?: string;
  /** Whether the skill is enabled by default */
  enabled_by_default?: boolean;
  /** Path to the skill definition file */
  path?: string;
}

/**
 * Information about an available agent.
 */
export interface AgentInfo {
  /** Unique identifier for the agent */
  id: string;
  /** Human-readable name of the agent */
  name: string;
  /** Description of the agent's capabilities */
  description: string;
  /** System prompt used by the agent */
  system_prompt?: string;
  /** Skills available to this agent */
  skills?: string[];
  /** Whether this is the default agent */
  is_default?: boolean;
}

/**
 * Response when listing available skills.
 */
export interface SkillListResponse {
  /** Array of available skills */
  skills: SkillInfo[];
  /** Total count of skills */
  count: number;
}

/**
 * Response when listing available agents.
 */
export interface AgentListResponse {
  /** Array of available agents */
  agents: AgentInfo[];
  /** Total count of agents */
  count: number;
}

/**
 * Health check response from the API.
 */
export interface HealthResponse {
  /** Status of the API server */
  status: 'healthy' | 'degraded' | 'unhealthy';
  /** Version of the API */
  version?: string;
  /** Timestamp of the health check */
  timestamp: string;
  /** Optional details about system components */
  details?: Record<string, unknown>;
}

/**
 * API error response structure.
 */
export interface APIErrorResponse {
  /** Error message */
  error: string;
  /** Error code for programmatic handling */
  code?: string;
  /** Additional error details */
  details?: Record<string, unknown>;
  /** HTTP status code */
  status?: number;
}

/**
 * Type guard to check if a response is an error.
 *
 * @param response - The response to check
 * @returns True if the response is an APIErrorResponse
 */
export function isAPIError(response: unknown): response is APIErrorResponse {
  return (
    typeof response === 'object' &&
    response !== null &&
    'error' in response &&
    typeof (response as APIErrorResponse).error === 'string'
  );
}

/**
 * Pagination parameters for listing endpoints.
 */
export interface PaginationParams {
  /** Number of items per page */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
  /** Field to sort by */
  sort_by?: string;
  /** Sort direction */
  sort_order?: 'asc' | 'desc';
}

/**
 * Filter parameters for session listing.
 */
export interface SessionFilterParams extends PaginationParams {
  /** Filter by agent ID */
  agent_id?: string;
  /** Filter by tag */
  tag?: string;
  /** Filter by date range start */
  from_date?: string;
  /** Filter by date range end */
  to_date?: string;
  /** Search query for title/content */
  search?: string;
}
