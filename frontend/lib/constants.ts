// API URL points to local Next.js proxy (API key is added server-side)
export const API_URL = '/api/proxy';

// WebSocket URL for direct browser-to-backend connection (uses JWT)
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat';

export const DEFAULT_AGENT_ID = process.env.NEXT_PUBLIC_DEFAULT_AGENT_ID || null;

export const STORAGE_KEYS = {
  SELECTED_AGENT: 'claude-chat-selected-agent',
  THEME: 'claude-chat-theme',
  SIDEBAR_OPEN: 'claude-chat-sidebar-open',
} as const;

export const QUERY_KEYS = {
  AGENTS: 'agents',
  SESSIONS: 'sessions',
  SESSION_HISTORY: 'session-history',
} as const;

export const RECONNECT_DELAY = 3000;
export const MAX_RECONNECT_ATTEMPTS = 5;
