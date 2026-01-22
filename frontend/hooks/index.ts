/**
 * Hooks Index
 *
 * Central export point for all custom React hooks.
 * Import hooks from this file for convenience.
 *
 * @module hooks
 *
 * @example
 * ```tsx
 * import {
 *   useClaudeChat,
 *   useSessions,
 *   useTheme,
 *   useAutoResize
 * } from '@/hooks';
 * ```
 */

// Chat functionality
export { useClaudeChat } from './use-claude-chat';

// Session management
export { useSessions } from './use-sessions';

// Agent management
export { useAgents } from './use-agents';

// Theme management
export { useTheme } from './use-theme';

// UI utilities
export { useAutoResize } from './use-auto-resize';

// Keyboard shortcuts
export { useKeyboardShortcuts } from './use-keyboard-shortcuts';

// WebSocket connection
export { useWebSocket } from './use-websocket';
export type { ConnectionState } from './use-websocket';
