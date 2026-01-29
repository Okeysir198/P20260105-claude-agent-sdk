'use client';

import { useChatStore } from '@/lib/store/chat-store';
import { StatusIndicator } from './status-indicator';
import { AgentSwitcher } from '@/components/agent/agent-switcher';
import { Button } from '@/components/ui/button';
import { PanelLeft, PanelRight, Plus, Sun, Moon } from 'lucide-react';
import { useUIStore } from '@/lib/store/ui-store';
import { useTheme } from 'next-themes';
import { useRouter } from 'next/navigation';

export function ChatHeader() {
  const router = useRouter();
  const agentId = useChatStore((s) => s.agentId);
  const status = useChatStore((s) => s.connectionStatus);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const { theme, setTheme } = useTheme();

  return (
    <header className="flex h-10 items-center justify-between border-b bg-background px-2 sm:px-4 shrink-0 fixed top-0 left-0 right-0 z-[60] md:static md:z-0">
      {/* Left: Sidebar toggle, agent selector, status */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? <PanelLeft className="h-3.5 w-3.5" /> : <PanelRight className="h-3.5 w-3.5" />}
        </Button>
        {agentId && <AgentSwitcher />}
        {agentId && <StatusIndicator status={status} />}
      </div>

      {/* Right: Theme toggle and new chat */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </Button>

        {agentId && (
          <Button
            onClick={() => {
              const store = useChatStore.getState();
              store.setAgentId(null);
              store.setSessionId(null);
              store.clearMessages();
              store.setConnectionStatus('disconnected');
              router.push('/');
            }}
            className="gap-2 h-7 px-3 bg-foreground hover:bg-foreground/90 text-background font-medium shadow-sm dark:shadow-none dark:border dark:border-border text-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </Button>
        )}
      </div>
    </header>
  );
}
