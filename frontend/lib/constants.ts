import { config } from './config';

export const API_URL = config.api.baseUrl;
export const WS_URL = config.api.wsUrl;

export const QUERY_KEYS = {
  AGENTS: config.queryKeys.agents,
  SESSIONS: config.queryKeys.sessions,
  SESSION_HISTORY: config.queryKeys.sessionHistory,
  SESSION_SEARCH: config.queryKeys.sessionSearch,
  FILES: config.queryKeys.files,
} as const;

export const RECONNECT_DELAY = config.websocket.reconnectDelay;
export const MAX_RECONNECT_ATTEMPTS = config.websocket.maxReconnectAttempts;
