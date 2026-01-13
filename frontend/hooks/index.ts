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

// Theme management
export { useTheme } from './use-theme';

// UI utilities
export { useAutoResize } from './use-auto-resize';

// SSE streaming
export { useSSEStream, parseSSEStream } from './use-sse-stream';
