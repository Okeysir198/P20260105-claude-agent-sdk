'use client';

import { useEffect } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { AgentGrid } from '@/components/agent/agent-grid';
import { ChatContainer } from '@/components/chat/chat-container';
import { ChatHeader } from '@/components/chat/chat-header';
import { SessionSidebar } from '@/components/session/session-sidebar';

export default function HomePage() {
  const agentId = useChatStore((s) => s.agentId);

  // Initialize agentId from localStorage on mount
  useEffect(() => {
    const savedAgentId = localStorage.getItem('claude-chat-selected-agent');
    if (savedAgentId && !agentId) {
      useChatStore.getState().setAgentId(savedAgentId);
    }
  }, [agentId]);

  // Save agentId to localStorage when it changes
  useEffect(() => {
    if (agentId) {
      localStorage.setItem('claude-chat-selected-agent', agentId);
    }
  }, [agentId]);

  return (
    <div className="flex h-screen overflow-hidden">
      <SessionSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <ChatHeader />
        <div className="flex-1 overflow-hidden">
          {!agentId ? <AgentGrid /> : <ChatContainer />}
        </div>
      </main>
    </div>
  );
}
