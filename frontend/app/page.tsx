'use client';

import { useState, useCallback, useEffect } from 'react';
import { ChatContainer } from '@/components/chat';
import { SessionSidebar } from '@/components/session';
import { useAgents } from '@/hooks/use-agents';

export default function Home() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  // Fetch available agents
  const { agents, loading: agentsLoading, defaultAgent } = useAgents();

  // Set default agent when agents are loaded
  useEffect(() => {
    if (!selectedAgentId && defaultAgent) {
      setSelectedAgentId(defaultAgent.agent_id);
    }
  }, [selectedAgentId, defaultAgent]);

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

      {/* Main chat area with header for agent selection */}
      <ChatContainer
        className="flex-1"
        selectedSessionId={currentSessionId}
        onSessionChange={setCurrentSessionId}
        showHeader={true}
        agents={agents}
        selectedAgentId={selectedAgentId}
        onAgentChange={handleAgentChange}
        agentsLoading={agentsLoading}
      />
    </main>
  );
}
