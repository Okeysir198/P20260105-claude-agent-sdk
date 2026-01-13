'use client';

import { useState, useCallback } from 'react';
import { ChatContainer } from '@/components/chat';
import { SessionSidebar } from '@/components/session';
import { ThemeToggle } from '@/components/theme-toggle';
import { cn } from '@/lib/utils';

export default function Home() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  return (
    <main className="flex h-screen bg-[var(--claude-background)]">
      {/* Sidebar */}
      <SessionSidebar
        currentSessionId={currentSessionId}
        onSessionSelect={setCurrentSessionId}
        onNewSession={() => setCurrentSessionId(null)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
        className="border-r border-[var(--claude-border)]"
      />

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header with theme toggle */}
        <header className="flex items-center justify-between px-4 py-2 border-b border-[var(--claude-border)]">
          <h1 className="font-serif text-lg text-[var(--claude-foreground)]">Claude Chat</h1>
          <ThemeToggle />
        </header>

        {/* Chat */}
        <ChatContainer
          className="flex-1"
          selectedSessionId={currentSessionId}
          onSessionChange={setCurrentSessionId}
        />
      </div>
    </main>
  );
}
