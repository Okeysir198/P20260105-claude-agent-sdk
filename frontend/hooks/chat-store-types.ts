/**
 * Type definitions for chat store context used in event handlers.
 * Provides a subset of the chat store interface needed by handlers.
 *
 * @module chat-store-types
 */

import type { ChatMessage, ConnectionStatus } from '@/types';

/**
 * Subset of chat store methods and state needed by event handlers.
 * This interface defines the contract between the hook and event handlers.
 */
export interface ChatStore {
  messages: ChatMessage[];
  setConnectionStatus: (status: ConnectionStatus) => void;
  setSessionId: (id: string | null) => void;
  setStreaming: (streaming: boolean) => void;
  setCancelling: (cancelling: boolean) => void;
  setCompacting: (compacting: boolean) => void;
  setPendingMessage: (message: string | null) => void;
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (updater: (msg: ChatMessage) => ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
}
