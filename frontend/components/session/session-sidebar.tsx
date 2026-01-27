'use client';
import { useEffect, useRef } from 'react';
import { useSessions } from '@/hooks/use-sessions';
import { useChatStore } from '@/lib/store/chat-store';
import { useUIStore } from '@/lib/store/ui-store';
import { SessionItem } from './session-item';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Bot, X, LogOut, User } from 'lucide-react';
import { useAuth } from '@/components/providers/auth-provider';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export function SessionSidebar() {
  const { user, logout } = useAuth();
  const { data: sessions, isLoading } = useSessions();
  const sessionId = useChatStore((s) => s.sessionId);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const setAgentId = useChatStore((s) => s.setAgentId);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const hadSessionsRef = useRef(false);

  // Track if we've ever had sessions
  useEffect(() => {
    if (sessions && sessions.length > 0) {
      hadSessionsRef.current = true;
    }
  }, [sessions]);

  // Clear chat only when sessions were previously populated and are now all deleted
  // This prevents clearing state during first session creation (race condition)
  useEffect(() => {
    if (!isLoading && sessions && sessions.length === 0 && sessionId && hadSessionsRef.current) {
      setSessionId(null);
      setAgentId(null);
      clearMessages();
      hadSessionsRef.current = false;
    }
  }, [sessions, sessionId, isLoading, setSessionId, setAgentId, clearMessages]);

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="flex h-12 items-center justify-between border-b px-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <h1 className="text-base font-semibold whitespace-nowrap">Agent Chat</h1>
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

      {/* User profile at bottom */}
      {user && (
        <div className="border-t p-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="w-full justify-start gap-3 h-auto py-2 px-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <User className="h-4 w-4" />
                </div>
                <div className="flex flex-col items-start text-left">
                  <span className="text-sm font-medium">{user.full_name || user.username}</span>
                  <span className="text-xs text-muted-foreground">{user.role}</span>
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuLabel>
                {user.username}
                <p className="text-xs font-normal text-muted-foreground">{user.role}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </div>
  );
}
