import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface QueuedMessage {
  id: string;
  content: string;
  timestamp: Date;
}

interface MessageQueueState {
  queuedMessages: QueuedMessage[];

  enqueueMessage: (content: string) => void;
  dequeueMessage: (id: string) => void;
  clearQueue: () => void;
  getQueueLength: () => number;
  getQueuedMessages: () => QueuedMessage[];
}

export const useMessageQueueStore = create<MessageQueueState>()(
  persist(
    (set, get) => ({
      queuedMessages: [],

      enqueueMessage: (content) => set((state) => ({
        queuedMessages: [
          ...state.queuedMessages,
          {
            id: crypto.randomUUID(),
            content,
            timestamp: new Date(),
          }
        ]
      })),

      dequeueMessage: (id) => set((state) => ({
        queuedMessages: state.queuedMessages.filter(msg => msg.id !== id)
      })),

      clearQueue: () => set({ queuedMessages: [] }),

      getQueueLength: () => get().queuedMessages.length,

      getQueuedMessages: () => get().queuedMessages,
    }),
    {
      name: 'message-queue-storage',
    }
  )
);
