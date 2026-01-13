/**
 * Components Index
 *
 * Barrel export for all UI components in the Claude Chat UI package.
 * This provides a convenient single import point for all components.
 *
 * @module components
 *
 * @example
 * ```tsx
 * import {
 *   ChatContainer,
 *   MessageList,
 *   SessionSidebar,
 *   ThemeProvider
 * } from '@/components';
 * ```
 */

// =============================================================================
// Chat Components
// =============================================================================
export {
  ChatContainer,
  ChatHeader,
  ChatInput,
  MessageItem,
  MessageList,
  UserMessage,
  AssistantMessage,
  ToolUseMessage,
  ToolResultMessage,
  TypingIndicator,
  ErrorMessage,
} from './chat';

// =============================================================================
// Session Components
// =============================================================================
export {
  SessionSidebar,
  SessionItem,
  NewSessionButton,
} from './session';

// =============================================================================
// Providers
// =============================================================================
export { ThemeProvider, useThemeContext } from './providers/theme-provider';

// =============================================================================
// UI Primitives (from shadcn/ui)
// =============================================================================
export { Button, buttonVariants } from './ui/button';
export type { ButtonProps } from './ui/button';

export { Badge, badgeVariants } from './ui/badge';
export type { BadgeProps } from './ui/badge';

export { Textarea } from './ui/textarea';

export { ScrollArea, ScrollBar } from './ui/scroll-area';

export {
  Skeleton,
  SkeletonText,
  SkeletonCircle,
  SkeletonCard,
  SkeletonMessage,
} from './ui/skeleton';

export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
  SimpleTooltip,
} from './ui/tooltip';
