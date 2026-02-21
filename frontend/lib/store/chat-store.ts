import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage, ConnectionStatus } from '@/types';

interface PendingFileUpload {
  file: File;
  name: string;
}

interface ChatState {
  messages: ChatMessage[];
  sessionId: string | null;
  agentId: string | null;
  isStreaming: boolean;
  isCancelling: boolean;
  isCompacting: boolean;
  connectionStatus: ConnectionStatus;
  pendingMessage: string | null;
  pendingFiles: PendingFileUpload[];

  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (updater: (msg: ChatMessage) => ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  setSessionId: (id: string | null) => void;
  setAgentId: (id: string | null) => void;
  setStreaming: (streaming: boolean) => void;
  setCancelling: (cancelling: boolean) => void;
  setCompacting: (compacting: boolean) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setPendingMessage: (message: string | null) => void;
  setPendingFiles: (files: PendingFileUpload[]) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      sessionId: null,
      agentId: null,
      isStreaming: false,
      isCancelling: false,
      isCompacting: false,
      connectionStatus: 'disconnected',
      pendingMessage: null,
      pendingFiles: [],

      addMessage: (message) => set({ messages: [...get().messages, message] }),
      updateLastMessage: (updater) => set((state) => {
        const messages = [...state.messages];
        if (messages.length > 0) {
          messages[messages.length - 1] = updater(messages[messages.length - 1]);
        }
        return { messages };
      }),
      setMessages: (messages) => set({ messages }),
      setSessionId: (id) => set({ sessionId: id }),
      setAgentId: (id) => set({ agentId: id }),
      setStreaming: (streaming) => set({ isStreaming: streaming }),
      setCancelling: (cancelling) => set({ isCancelling: cancelling }),
      setCompacting: (compacting) => set({ isCompacting: compacting }),
      setConnectionStatus: (status) => set({ connectionStatus: status }),
      setPendingMessage: (message) => set({ pendingMessage: message }),
      setPendingFiles: (files) => set({ pendingFiles: files }),
      clearMessages: () => set({ messages: [], pendingMessage: null, pendingFiles: [] }),
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
