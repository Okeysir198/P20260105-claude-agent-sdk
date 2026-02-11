/**
 * Centralized configuration for the frontend application.
 * All hardcoded values should be defined here for easy maintenance.
 */

export const config = {
  api: {
    baseUrl: '/api/proxy',
    wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat',
  },
  auth: {
    tokenEndpoint: '/api/auth/token',
    refreshEndpoint: '/api/auth/refresh',
  },
  websocket: {
    reconnectDelay: 3000,
    maxReconnectAttempts: 5,
  },
  storage: {
    selectedAgent: 'claude-chat-selected-agent',
    sidebarWidth: 'claude-chat-sidebar-width',
    theme: 'claude-chat-theme',
    sidebarOpen: 'claude-chat-sidebar-open',
    kanbanWidth: 'claude-chat-kanban-width',
  },
  sidebar: {
    minWidth: 240,
    maxWidth: 500,
    defaultWidth: 280,
  },
  kanban: {
    minWidth: 260,
    maxWidth: 600,
    defaultWidth: 320,
    breakpoints: {
      narrow: 320,
      compact: 400,
      standard: 500,
    },
  },
  queryKeys: {
    agents: 'agents',
    sessions: 'sessions',
    sessionHistory: 'session-history',
    sessionSearch: 'session-search',
    files: 'files',
  },
} as const;

// Type helper for config keys
export type Config = typeof config;
