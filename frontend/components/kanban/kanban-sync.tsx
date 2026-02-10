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
  const lastSyncedRef = useRef<string>('');

  useEffect(() => {
    if (!isOpen) return;

    // Build a fingerprint from message count + last few message IDs
    // This catches both new messages and message updates (tool_result arrivals)
    const lastIds = messages.slice(-5).map((m) => `${m.id}:${m.role}`).join(',');
    const fingerprint = `${messages.length}|${lastIds}`;

    if (fingerprint !== lastSyncedRef.current) {
      lastSyncedRef.current = fingerprint;
      syncFromMessages(messages);
    }
  }, [messages, isOpen, syncFromMessages]);

  // Also sync when panel opens (to catch up on messages)
  useEffect(() => {
    if (isOpen) {
      const currentMessages = useChatStore.getState().messages;
      syncFromMessages(currentMessages);
      const lastIds = currentMessages.slice(-5).map((m) => `${m.id}:${m.role}`).join(',');
      lastSyncedRef.current = `${currentMessages.length}|${lastIds}`;
    }
  }, [isOpen, syncFromMessages]);

  return null;
}
