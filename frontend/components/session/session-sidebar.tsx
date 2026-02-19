'use client';
import { useSessions, useBatchDeleteSessions } from '@/hooks/use-sessions';
import { useChatStore } from '@/lib/store/chat-store';
import { useUIStore } from '@/lib/store/ui-store';
import { SidebarTabs } from './sidebar-tabs';
import { SessionListContent } from './session-list-content';
import { FileManagerContent } from '../files/file-manager-content';
import { Button } from '@/components/ui/button';
import { Bot, X, LogOut, User, Mail, Settings } from 'lucide-react';
import { useAuth } from '@/components/providers/auth-provider';
import { useRouter } from 'next/navigation';
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
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const activeTab = useUIStore((s) => s.sidebarActiveTab);
  const setActiveTab = useUIStore((s) => s.setSidebarActiveTab);
  const router = useRouter();

  return (
    <div className="flex h-full w-full flex-col bg-background">
      {/* Header */}
      <div className="flex h-10 items-center justify-between border-b px-2">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
            <Bot className="h-3.5 w-3.5 text-white" />
          </div>
          <h1 className="text-sm font-semibold truncate">Claude Agent SDK</h1>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSidebarOpen(false)}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Tab switcher */}
      <SidebarTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Content area */}
      <div className="flex-1 overflow-hidden min-h-0">
        {activeTab === 'sessions' ? (
          <SessionListContent
            sessions={sessions || []}
            currentSessionId={sessionId}
            onSessionSelect={(id) => {
              // Session selection is handled by SessionItem
            }}
            onNewSession={() => {
              // New session is handled by the main page
            }}
            isLoading={isLoading}
          />
        ) : (
          <FileManagerContent sessionId={sessionId || ''} />
        )}
      </div>

      {/* User profile at bottom */}
      {user && (
        <div className="border-t p-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="w-full justify-start gap-2 h-8 px-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <User className="h-3 w-3" />
                </div>
                <span className="text-sm truncate">{user.full_name || user.username}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48">
              <DropdownMenuLabel className="py-1.5">
                <span className="text-sm">{user.username}</span>
                <p className="text-[10px] font-normal text-muted-foreground">{user.role}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => router.push('/email-integration')}
                className="text-sm py-1.5"
              >
                <Mail className="mr-2 h-3.5 w-3.5" />
                Email Integration
              </DropdownMenuItem>
              {user.role === 'admin' && (
                <DropdownMenuItem
                  onClick={() => router.push('/admin')}
                  className="text-sm py-1.5"
                >
                  <Settings className="mr-2 h-3.5 w-3.5" />
                  Admin Settings
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={logout} className="text-destructive text-sm py-1.5">
                <LogOut className="mr-2 h-3.5 w-3.5" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </div>
  );
}
