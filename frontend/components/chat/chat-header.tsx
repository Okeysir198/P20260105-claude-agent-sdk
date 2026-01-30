'use client';

import { useChatStore } from '@/lib/store/chat-store';
import { StatusIndicator } from './status-indicator';
import { SessionTitle } from './session-title';
import { Button } from '@/components/ui/button';
import { PanelLeft, PanelRight, Copy } from 'lucide-react';
import { useUIStore } from '@/lib/store/ui-store';
import { toast } from 'sonner';

function formatDuration(startTime: Date | null): string {
  if (!startTime) return '0m';
  const diff = Date.now() - new Date(startTime).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export function ChatHeader() {
  const sessionId = useChatStore((s) => s.sessionId);
  const agentId = useChatStore((s) => s.agentId);
  const status = useChatStore((s) => s.connectionStatus);
  const stats = useChatStore((s) => s.sessionStats);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);

  const copySessionId = () => {
    if (sessionId) {
      navigator.clipboard.writeText(sessionId);
      toast.success('Session ID copied');
    }
  };

  return (
    <header className="flex h-12 items-center justify-between border-b bg-background px-3 sm:px-4 shrink-0 fixed top-0 left-0 right-0 z-[60] md:static md:z-0">
      {/* Left: Sidebar toggle + Title */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelRight className="h-4 w-4" />
          )}
        </Button>
        <SessionTitle />
      </div>

      {/* Right: Status + Stats + Copy */}
      <div className="flex items-center gap-3">
        {agentId && <StatusIndicator status={status} compact />}

        {/* Inline stats - hidden on small screens */}
        {stats && (
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground">
            <span>{stats.turnCount} turn{stats.turnCount !== 1 ? 's' : ''}</span>
            <span className="text-muted-foreground/50">·</span>
            <span>${stats.totalCost.toFixed(2)}</span>
            <span className="text-muted-foreground/50">·</span>
            <span>{formatDuration(stats.startTime)}</span>
          </div>
        )}

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={copySessionId}
          title="Copy Session ID"
          disabled={!sessionId}
        >
          <Copy className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
