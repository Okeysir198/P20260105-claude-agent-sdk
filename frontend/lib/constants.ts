export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://cartrack-voice-agents-api.tt-ai.org/api/v1';
export const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

// Derive WebSocket URL from API URL
const getWebSocketUrl = () => {
  const envWsUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envWsUrl) return envWsUrl;

  // Convert HTTP API URL to WebSocket URL
  const apiUrl = API_URL.replace(/^https?:\/\//, '');
  const protocol = API_URL.startsWith('https') ? 'wss' : 'ws';
  return `${protocol}://${apiUrl}/ws/chat`;
};

export const WS_URL = getWebSocketUrl();

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
