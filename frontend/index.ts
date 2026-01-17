/**
 * Claude Chat UI - Main Export File
 *
 * This is the main entry point for the Claude Chat UI package.
 * It exports all components, hooks, types, and utilities needed
 * to build chat interfaces with the Claude Agent SDK.
 *
 * @packageDocumentation
 * @module claude-chat-ui
 */

// =============================================================================
// Chat Components
// =============================================================================
export { ChatContainer } from './components/chat/chat-container';
export { ChatHeader } from './components/chat/chat-header';
export { ChatInput } from './components/chat/chat-input';
export { MessageList } from './components/chat/message-list';
export { MessageItem } from './components/chat/message-item';
export { UserMessage } from './components/chat/user-message';
export { AssistantMessage } from './components/chat/assistant-message';
export { ToolUseMessage } from './components/chat/tool-use-message';
export { ToolResultMessage } from './components/chat/tool-result-message';
export { TypingIndicator } from './components/chat/typing-indicator';
export { ErrorMessage } from './components/chat/error-message';

// =============================================================================
// Session Components
// =============================================================================
export { SessionSidebar } from './components/session/session-sidebar';
export { SessionItem } from './components/session/session-item';
export { NewSessionButton } from './components/session/new-session-button';

// =============================================================================
// Providers
// =============================================================================
export { ThemeProvider, useThemeContext } from './components/providers/theme-provider';

// =============================================================================
// Hooks
// =============================================================================
export { useClaudeChat } from './hooks/use-claude-chat';
export { useSessions } from './hooks/use-sessions';
export { useTheme } from './hooks/use-theme';
export { useAutoResize } from './hooks/use-auto-resize';
export { useSSEStream, parseSSEStream } from './hooks/use-sse-stream';

// =============================================================================
// Types
// =============================================================================

// SSE Event Types
export type {
  SessionIdEvent,
  TextDeltaEvent,
  ToolUseEvent,
  ToolResultEvent,
  DoneEvent,
  ErrorEvent,
  SSEEventType,
  ParsedSSEEvent,
  RawSSEEvent,
  SSEEventParser,
} from './types/events';
export { isSSEEventType } from './types/events';

// Message Types
export type {
  BaseMessage,
  UserMessage as UserMessageType,
  AssistantMessage as AssistantMessageType,
  ToolUseMessage as ToolUseMessageType,
  ToolResultMessage as ToolResultMessageType,
  SystemMessage,
  Message,
  ConversationState,
} from './types/messages';
export {
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
} from './types/messages';

// Session Types
export type {
  SessionInfo,
  SessionTotals,
  SessionListResponse,
  CreateConversationRequest,
  SendMessageRequest,
  ResumeSessionRequest,
  ConversationResponse,
  InterruptRequest,
  InterruptResponse,
  SkillInfo,
  AgentInfo,
  SkillListResponse,
  AgentListResponse,
  HealthResponse,
  APIErrorResponse,
  PaginationParams,
  SessionFilterParams,
} from './types/sessions';
export { isAPIError } from './types/sessions';

// Theme Types
export type {
  ClaudeThemeColors,
  ThemeMode,
  BorderRadiusPreset,
  FontFamilyPreset,
  ThemeConfig,
  ThemeContextValue,
} from './types/theme';
export {
  LIGHT_THEME_COLORS,
  DARK_THEME_COLORS,
  DEFAULT_THEME_CONFIG,
  BORDER_RADIUS_VALUES,
  FONT_FAMILY_VALUES,
  resolveThemeColors,
  isThemeDark,
} from './types/theme';

// =============================================================================
// Utilities
// =============================================================================
export { cn } from './lib/utils';
export { CLAUDE_COLORS, DEFAULT_API_URL, SEMANTIC_COLORS, ANIMATION_DURATION, BREAKPOINTS } from './lib/constants';

// Animation variants and utilities
export {
  // Message animations
  messageVariants,
  messageListVariants,
  // Fade animations
  fadeScaleVariants,
  // Slide animations
  slideRightVariants,
  // Expand/collapse animations
  toolExpandVariants,
  // Interactive element animations
  chevronVariants,
  // Typing/loading animations
  typingDotVariants,
  cursorVariants,
  // Transition presets
  springTransition,
  smoothSpring,
  quickTween,
  standardTween,
  // Stagger configurations
  staggerConfig,
  createStaggerVariants,
  // Utility functions
  withDelay,
} from './lib/animations';
