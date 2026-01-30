// types/api.ts
export interface AgentInfo {
  agent_id: string;
  name: string;
  description: string;
  model: string;
  is_default: boolean;
}

export interface SessionInfo {
  session_id: string;
  name: string | null;
  first_message: string | null;
  created_at: string;
  turn_count: number;
  user_id: string | null;
  agent_id: string | null;
}

export interface SessionResponse {
  session_id: string;
  status: string;
  resumed: boolean;
}

export interface SessionHistoryResponse {
  session_id: string;
  messages: HistoryMessage[];
  turn_count: number;
  first_message: string | null;
}

export interface HistoryMessage {
  role: string;
  /** Message content - can be plain string or multi-part content blocks */
  content: string | any;
  timestamp?: string;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
}

export interface CreateSessionRequest {
  agent_id?: string;
}

export interface ResumeSessionRequest {
  initial_message?: string;
}

export interface CloseSessionResponse {
  status: string;
}

export interface DeleteSessionResponse {
  status: string;
}

export interface AgentsListResponse {
  agents: AgentInfo[];
}

// Auth types
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface UpdateSessionRequest {
  name?: string | null;
}

export interface BatchDeleteSessionsRequest {
  session_ids: string[];
}

export interface SearchResult {
  session_id: string;
  name: string | null;
  first_message: string | null;
  created_at: string;
  turn_count: number;
  agent_id: string | null;
  relevance_score: number;
  match_count: number;
  snippet: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total_count: number;
  query: string;
}
