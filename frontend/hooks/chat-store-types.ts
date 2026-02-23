import type { ChatMessage, ConnectionStatus } from '@/types';

export interface ChatStore {
  setConnectionStatus: (status: ConnectionStatus) => void;
  setSessionId: (id: string | null) => void;
  setCwdId: (id: string | null) => void;
  setStreaming: (streaming: boolean) => void;
  setCancelling: (cancelling: boolean) => void;
  setCompacting: (compacting: boolean) => void;
  setPendingMessage: (message: string | null) => void;
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (updater: (msg: ChatMessage) => ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
}
