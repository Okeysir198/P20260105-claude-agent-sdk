'use client';

import { useEffect, useRef } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useKanbanStore } from '@/lib/store/kanban-store';

/**
 * Invisible component that syncs chat messages to kanban store.
 * Only runs sync when the kanban panel is open (performance optimization).
 */
export function KanbanSync() {
  const messages = useChatStore((s) => s.messages);
  const isOpen = useKanbanStore((s) => s.isOpen);
  const syncFromMessages = useKanbanStore((s) => s.syncFromMessages);
  const prevMessageCountRef = useRef(0);

  useEffect(() => {
    if (!isOpen) return;

    // Only sync when messages actually change
    if (messages.length !== prevMessageCountRef.current) {
      prevMessageCountRef.current = messages.length;
      syncFromMessages(messages);
    }
  }, [messages, isOpen, syncFromMessages]);

  // Also sync when panel opens (to catch up on messages)
  useEffect(() => {
    if (isOpen) {
      const currentMessages = useChatStore.getState().messages;
      syncFromMessages(currentMessages);
      prevMessageCountRef.current = currentMessages.length;
    }
  }, [isOpen, syncFromMessages]);

  return null;
}
