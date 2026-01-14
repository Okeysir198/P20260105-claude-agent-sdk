'use client';

import { useState, useCallback } from 'react';
import { ChatContainer } from '@/components/chat';
import { SessionSidebar } from '@/components/session';
import { cn } from '@/lib/utils';

export default function Home() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const handleSessionDeleted = useCallback((deletedSessionId: string) => {
    // Clear current session if it was the one deleted
    if (currentSessionId === deletedSessionId) {
      setCurrentSessionId(null);
    }
  }, [currentSessionId]);

  return (
    <main className="flex h-screen bg-surface-primary">
      {/* Sidebar */}
      <SessionSidebar
        currentSessionId={currentSessionId}
        onSessionSelect={setCurrentSessionId}
        onNewSession={() => setCurrentSessionId(null)}
        onSessionDeleted={handleSessionDeleted}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
      />

      {/* Main chat area - clean layout without redundant header */}
      <ChatContainer
        className="flex-1"
        selectedSessionId={currentSessionId}
        onSessionChange={setCurrentSessionId}
        showHeader={false}
      />
    </main>
  );
}
