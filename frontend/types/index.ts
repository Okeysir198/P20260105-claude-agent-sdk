/**
 * Type Definitions for Claude Chat UI
 * @module types
 */

// SSE Event Types
export {
  type SessionIdEvent,
  type TextDeltaEvent,
  type ToolUseEvent,
  type ToolResultEvent,
  type DoneEvent,
  type ErrorEvent,
  type SSEEventType,
  type ParsedSSEEvent,
  type RawSSEEvent,
  type SSEEventParser,
  isSSEEventType,
} from './events';

// Message Types
export {
  type BaseMessage,
  type UserMessage,
  type AssistantMessage,
  type ToolUseMessage,
  type ToolResultMessage,
  type SystemMessage,
  type Message,
  type MessageRole,
  type ConversationState,
  type HistoryMessage,
  type SessionHistoryResponse,
  INITIAL_CONVERSATION_STATE,
  isUserMessage,
  isAssistantMessage,
  isToolUseMessage,
  isToolResultMessage,
  isSystemMessage,
  createMessageId,
  createUserMessage,
  createAssistantMessage,
  createToolUseMessage,
  createToolResultMessage,
  convertHistoryToMessages,
} from './messages';

// Session Types
export {
  type SessionInfo,
  type SessionTotals,
  type SessionListResponse,
  type CreateConversationRequest,
  type SendMessageRequest,
  type ResumeSessionRequest,
  type ConversationResponse,
  type InterruptRequest,
  type InterruptResponse,
  type SkillInfo,
  type AgentInfo,
  type SkillListResponse,
  type AgentListResponse,
  type HealthResponse,
  type APIErrorResponse,
  type PaginationParams,
  type SessionFilterParams,
  isAPIError,
} from './sessions';

// Theme Types
export {
  type ClaudeThemeColors,
  type ThemeMode,
  type BorderRadiusPreset,
  type FontFamilyPreset,
  type ThemeConfig,
  type ThemeContextValue,
  LIGHT_THEME_COLORS,
  DARK_THEME_COLORS,
  DEFAULT_THEME_CONFIG,
  BORDER_RADIUS_VALUES,
  FONT_FAMILY_VALUES,
  resolveThemeColors,
  isThemeDark,
} from './theme';
