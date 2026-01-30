import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage, ConnectionStatus } from '@/types';

export interface SessionStats {
  totalCost: number;
  turnCount: number;
  startTime: Date | null;
}

interface ChatState {
  messages: ChatMessage[];
  sessionId: string | null;
  agentId: string | null;
  isStreaming: boolean;
  connectionStatus: ConnectionStatus;
  pendingMessage: string | null;
  sessionStats: SessionStats | null;

  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (updater: (msg: ChatMessage) => ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  setSessionId: (id: string | null) => void;
  setAgentId: (id: string | null) => void;
  setStreaming: (streaming: boolean) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setPendingMessage: (message: string | null) => void;
  clearMessages: () => void;
  setSessionStats: (stats: SessionStats) => void;
  resetSessionStats: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      sessionId: null,
      agentId: null,
      isStreaming: false,
      connectionStatus: 'disconnected',
      pendingMessage: null,
      sessionStats: null,

      addMessage: (message) => {
        // Defensive: skip undefined or invalid messages
        if (!message || !message.role) {
          console.warn('[ChatStore] Attempted to add invalid message:', message);
          return;
        }
        set({ messages: [...get().messages, message] });
      },
      updateLastMessage: (updater) => set((state) => {
        const messages = [...state.messages];
        if (messages.length > 0) {
          messages[messages.length - 1] = updater(messages[messages.length - 1]);
        }
        return { messages };
      }),
      setMessages: (messages) => {
        // Filter out undefined or invalid messages
        const validMessages = messages.filter(m => m && m.role);
        if (validMessages.length !== messages.length) {
          console.warn(`[ChatStore] Filtered ${messages.length - validMessages.length} invalid messages`);
        }
        set({ messages: validMessages });
      },
      setSessionId: (id) => set({ sessionId: id }),
      setAgentId: (id) => set({ agentId: id }),
      setStreaming: (streaming) => set({ isStreaming: streaming }),
      setConnectionStatus: (status) => set({ connectionStatus: status }),
      setPendingMessage: (message) => set({ pendingMessage: message }),
      clearMessages: () => set({ messages: [], pendingMessage: null }),
      setSessionStats: (stats) => set({ sessionStats: stats }),
      resetSessionStats: () => set({ sessionStats: null }),
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        sessionId: state.sessionId,
        agentId: state.agentId,
      }),
    }
  )
);
