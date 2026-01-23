'use client';
import { useSessions } from '@/hooks/use-sessions';
import { useChatStore } from '@/lib/store/chat-store';
import { useUIStore } from '@/lib/store/ui-store';
import { SessionItem } from './session-item';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { X, Bot } from 'lucide-react';

export function SessionSidebar() {
  const { data: sessions, isLoading } = useSessions();
  const sessionId = useChatStore((s) => s.sessionId);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);

  if (!sidebarOpen) {
    return null;
  }

  return (
    <div className="flex h-full w-80 flex-col border-r">
      <div className="flex h-12 items-center justify-between border-b px-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <h1 className="text-base font-semibold">Agent Chat</h1>
        </div>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSidebarOpen(false)}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-1 px-4 pt-4 pb-4">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
              ))}
            </div>
          ) : sessions && sessions.length > 0 ? (
            sessions.map((session) => (
              <SessionItem
                key={session.session_id}
                session={session}
                isActive={session.session_id === sessionId}
              />
            ))
          ) : (
            <p className="px-2 text-sm text-muted-foreground">No conversations yet</p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
