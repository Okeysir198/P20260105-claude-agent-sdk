/**
 * Application constants - re-exported from centralized config.
 * This file maintains backward compatibility while using the new config module.
 */

import { config } from './config';

// API URL points to local Next.js proxy (API key is added server-side)
export const API_URL = config.api.baseUrl;

// WebSocket URL for direct browser-to-backend connection (uses JWT)
export const WS_URL = config.api.wsUrl;

export const DEFAULT_AGENT_ID = process.env.NEXT_PUBLIC_DEFAULT_AGENT_ID || null;

export const STORAGE_KEYS = {
  SELECTED_AGENT: config.storage.selectedAgent,
  THEME: config.storage.theme,
  SIDEBAR_OPEN: config.storage.sidebarOpen,
  SIDEBAR_WIDTH: config.storage.sidebarWidth,
} as const;

export const QUERY_KEYS = {
  AGENTS: config.queryKeys.agents,
  SESSIONS: config.queryKeys.sessions,
  SESSION_HISTORY: config.queryKeys.sessionHistory,
  SESSION_SEARCH: config.queryKeys.sessionSearch,
  FILES: config.queryKeys.files,
} as const;

export const RECONNECT_DELAY = config.websocket.reconnectDelay;
export const MAX_RECONNECT_ATTEMPTS = config.websocket.maxReconnectAttempts;
