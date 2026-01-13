/**
 * Type Definitions for Claude Chat UI
 *
 * This barrel file exports all type definitions used throughout the Claude Chat UI.
 * Import types from this file for convenience:
 *
 * @example
 * ```typescript
 * import {
 *   Message,
 *   ParsedSSEEvent,
 *   SessionInfo,
 *   ThemeConfig
 * } from '@/types';
 * ```
 *
 * @module types
 */

// ============================================
// SSE Event Types
// ============================================
export {
  // Event data interfaces
  type SessionIdEvent,
  type TextDeltaEvent,
  type ToolUseEvent,
  type ToolResultEvent,
  type DoneEvent,
  type ErrorEvent,

  // Event type unions
  type SSEEventType,
  type ParsedSSEEvent,
  type RawSSEEvent,
  type SSEEventParser,

  // Type guards and utilities
  isSSEEventType,
} from './events';

// ============================================
// Message Types
// ============================================
export {
  // Base and specific message interfaces
  type BaseMessage,
  type UserMessage,
  type AssistantMessage,
  type ToolUseMessage,
  type ToolResultMessage,
  type SystemMessage,

  // Union type for all messages
  type Message,

  // Conversation state
  type ConversationState,
  INITIAL_CONVERSATION_STATE,

  // Type guards
  isUserMessage,
  isAssistantMessage,
  isToolUseMessage,
  isToolResultMessage,
  isSystemMessage,

  // Factory functions
  createMessageId,
  createUserMessage,
  createAssistantMessage,
  createToolUseMessage,
  createToolResultMessage,
} from './messages';

// ============================================
// Session Types
// ============================================
export {
  // Session interfaces
  type SessionInfo,
  type SessionTotals,
  type SessionListResponse,

  // Request/Response types
  type CreateConversationRequest,
  type SendMessageRequest,
  type ResumeSessionRequest,
  type ConversationResponse,
  type InterruptRequest,
  type InterruptResponse,

  // Resource types
  type SkillInfo,
  type AgentInfo,
  type SkillListResponse,
  type AgentListResponse,

  // API types
  type HealthResponse,
  type APIErrorResponse,
  isAPIError,

  // Pagination/Filter types
  type PaginationParams,
  type SessionFilterParams,
} from './sessions';

// ============================================
// Theme Types
// ============================================
export {
  // Theme color interface
  type ClaudeThemeColors,

  // Theme type unions
  type ThemeMode,
  type BorderRadiusPreset,
  type FontFamilyPreset,

  // Theme configuration
  type ThemeConfig,
  type ThemeContextValue,

  // Theme constants
  LIGHT_THEME_COLORS,
  DARK_THEME_COLORS,
  DEFAULT_THEME_CONFIG,
  BORDER_RADIUS_VALUES,
  FONT_FAMILY_VALUES,

  // Theme utilities
  resolveThemeColors,
  isThemeDark,
} from './theme';
