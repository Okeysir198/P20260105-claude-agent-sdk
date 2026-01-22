'use client';

import { useState, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useAgents } from '@/hooks/use-agents';
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts';
import { BottomSheet } from '@/components/mobile';

// Dynamically import heavy components to reduce initial bundle size
const ChatContainer = dynamic(() => import('@/components/chat').then(mod => ({ default: mod.ChatContainer })), {
  loading: () => (
    <div className="flex-1 flex items-center justify-center">
      <div className="animate-pulse text-foreground-muted">Loading chat...</div>
    </div>
  ),
  ssr: false,
});

const SessionSidebar = dynamic(() => import('@/components/session').then(mod => ({ default: mod.SessionSidebar })), {
  loading: () => (
    <div className="w-64 border-r border-border animate-pulse" />
  ),
  ssr: false,
});

export default function Home() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  // Fetch available agents
  const { agents, loading: agentsLoading, defaultAgent } = useAgents();

  // Set default agent when agents are loaded
  useEffect(() => {
    if (!selectedAgentId && defaultAgent) {
      setSelectedAgentId(defaultAgent.agent_id);
    }
  }, [selectedAgentId, defaultAgent]);

  const handleNewChat = useCallback(() => {
    setCurrentSessionId(null);
  }, []);

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const handleSessionDeleted = useCallback((deletedSessionId: string) => {
    // Clear current session if it was the one deleted
    if (currentSessionId === deletedSessionId) {
      setCurrentSessionId(null);
    }
  }, [currentSessionId]);

  const handleAgentChange = useCallback((agentId: string) => {
    setSelectedAgentId(agentId);
    // Start a new session when agent changes
    setCurrentSessionId(null);
  }, []);

  const handleMobileMenuClose = useCallback(() => {
    setMobileMenuOpen(false);
  }, []);

  // Global keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: 'cmd+n',
      handler: handleNewChat,
      description: 'New chat',
    },
    {
      key: 'cmd+/',
      handler: handleToggleSidebar,
      description: 'Toggle sidebar',
    },
    {
      key: 'escape',
      handler: () => {
        if (mobileMenuOpen) {
          setMobileMenuOpen(false);
        }
      },
      description: 'Close mobile menu',
      preventDefault: false,
    },
  ]);

  return (
    <main className="flex h-screen bg-surface-primary overflow-hidden">
      {/* Desktop Sidebar - hidden on mobile, visible on md+ */}
      <div className="hidden md:block">
        <SessionSidebar
          currentSessionId={currentSessionId}
          onSessionSelect={setCurrentSessionId}
          onNewSession={handleNewChat}
          onSessionDeleted={handleSessionDeleted}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={handleToggleSidebar}
        />
      </div>

      {/* Mobile Bottom Sheet - only visible on mobile */}
      <BottomSheet
        isOpen={mobileMenuOpen}
        onClose={handleMobileMenuClose}
        title="Chats"
      >
        <div className="h-full">
          <SessionSidebar
            currentSessionId={currentSessionId}
            onSessionSelect={(sessionId) => {
              setCurrentSessionId(sessionId);
              handleMobileMenuClose();
            }}
            onNewSession={() => {
              handleNewChat();
              handleMobileMenuClose();
            }}
            onSessionDeleted={handleSessionDeleted}
            isCollapsed={false}
          />
        </div>
      </BottomSheet>

      {/* Main chat area with header for agent selection */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatContainer
          className="flex-1"
          selectedSessionId={currentSessionId}
          onSessionChange={setCurrentSessionId}
          showHeader={true}
          agents={agents}
          selectedAgentId={selectedAgentId}
          onAgentChange={handleAgentChange}
          agentsLoading={agentsLoading}
          mobileMenuOpen={mobileMenuOpen}
          onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)}
        />
      </div>
    </main>
  );
}
