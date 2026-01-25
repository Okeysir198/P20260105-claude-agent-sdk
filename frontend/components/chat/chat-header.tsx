'use client';

import { useChatStore } from '@/lib/store/chat-store';
import { StatusIndicator } from './status-indicator';
import { AgentSwitcher } from '@/components/agent/agent-switcher';
import { Button } from '@/components/ui/button';
import { PanelLeft, PanelRight, Plus, Sun, Moon } from 'lucide-react';
import { useUIStore } from '@/lib/store/ui-store';
import { useTheme } from 'next-themes';

export function ChatHeader() {
  const agentId = useChatStore((s) => s.agentId);
  const status = useChatStore((s) => s.connectionStatus);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const { theme, setTheme } = useTheme();

  return (
    <header className="flex h-12 items-center justify-between border-b bg-background px-4 pr-5 sm:px-4 shrink-0">
      {/* Left: Sidebar toggle, agent selector, status */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? <PanelLeft className="h-4 w-4" /> : <PanelRight className="h-4 w-4" />}
        </Button>
        {agentId && <AgentSwitcher />}
        {agentId && <StatusIndicator status={status} />}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 shrink-0"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        {agentId && (
          <Button
            onClick={() => {
              const store = useChatStore.getState();
              store.setAgentId(null);
              store.setSessionId(null);
              store.clearMessages();
              store.setConnectionStatus('disconnected');
            }}
            className="gap-2 h-9 px-4 bg-foreground hover:bg-foreground/90 text-background font-medium shadow-sm dark:shadow-none dark:border dark:border-border"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">New Chat</span>
          </Button>
        )}
      </div>
    </header>
  );
}
