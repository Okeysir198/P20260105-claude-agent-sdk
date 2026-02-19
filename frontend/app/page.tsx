'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useUIStore } from '@/lib/store/ui-store';
import { AgentGrid } from '@/components/agent/agent-grid';
import { ChatContainer } from '@/components/chat/chat-container';
import { ChatHeader } from '@/components/chat/chat-header';
import { SessionSidebar } from '@/components/session/session-sidebar';
import { KanbanBoard } from '@/components/kanban';
import { FilePreviewModal } from '@/components/files/file-preview-modal';
import { useKanbanStore } from '@/lib/store/kanban-store';
import { GripVertical } from 'lucide-react';
import { tokenService } from '@/lib/auth';
import { config } from '@/lib/config';
import { useAuth } from '@/components/providers/auth-provider';
import { useRouter, useParams } from 'next/navigation';

export default function HomePage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const agentId = useChatStore((s) => s.agentId);
  const kanbanOpen = useKanbanStore((s) => s.isOpen);
  const sessionId = useChatStore((s) => s.sessionId);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const setIsMobile = useUIStore((s) => s.setIsMobile);
  const hasInitialized = useRef(false);
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(config.storage.sidebarWidth);
      if (saved) return Math.max(config.sidebar.minWidth, Math.min(config.sidebar.maxWidth, parseInt(saved, 10)));
    }
    return config.sidebar.defaultWidth;
  });
  const [kanbanWidth, setKanbanWidth] = useState<number>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(config.storage.kanbanWidth);
      if (saved) return Math.max(config.kanban.minWidth, Math.min(config.kanban.maxWidth, parseInt(saved, 10)));
    }
    return config.kanban.defaultWidth;
  });
  const [isMobile, setIsMobileLocal] = useState(false);
  const isResizing = useRef(false);
  const isResizingKanban = useRef(false);
  const isUpdatingUrl = useRef(false);
  const lastProcessedSessionId = useRef<string | null>(null);

  // Initialize agentId from localStorage ONLY on first mount
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    // Initialize tokens for WebSocket (still needed)
    const initializeTokens = async () => {
      try {
        await tokenService.fetchTokens();
      } catch (err) {
        console.error('Failed to obtain JWT tokens:', err);
      }
    };
    initializeTokens();

    const savedAgentId = localStorage.getItem(config.storage.selectedAgent);
    if (savedAgentId && !useChatStore.getState().agentId) {
      useChatStore.getState().setAgentId(savedAgentId);
    }
  }, []);

  // Save sidebar width to localStorage
  useEffect(() => {
    localStorage.setItem(config.storage.sidebarWidth, sidebarWidth.toString());
  }, [sidebarWidth]);

  // Save kanban width to localStorage
  useEffect(() => {
    localStorage.setItem(config.storage.kanbanWidth, kanbanWidth.toString());
  }, [kanbanWidth]);

  // Save agentId to localStorage when it changes (clear when null)
  useEffect(() => {
    if (agentId) {
      localStorage.setItem(config.storage.selectedAgent, agentId);
    } else {
      localStorage.removeItem(config.storage.selectedAgent);
    }
  }, [agentId]);

  // Sync session ID with URL
  useEffect(() => {
    // Don't update URL if we're currently processing a URL change
    if (isUpdatingUrl.current) return;

    const rawSessionId = params.sessionId;
    const urlSessionId = Array.isArray(rawSessionId) ? rawSessionId[0] : rawSessionId || null;

    // Avoid processing the same session ID twice
    if (urlSessionId === lastProcessedSessionId.current) return;

    // If URL has a session ID different from current, load it
    if (urlSessionId && urlSessionId !== sessionId) {
      isUpdatingUrl.current = true;
      lastProcessedSessionId.current = urlSessionId;
      setSessionId(urlSessionId);
      // Reset flag after state update
      setTimeout(() => {
        isUpdatingUrl.current = false;
      }, 100);
    }
    // If session ID in store but not in URL, update URL
    else if (sessionId && sessionId !== urlSessionId) {
      isUpdatingUrl.current = true;
      lastProcessedSessionId.current = sessionId;
      router.push(`/s/${sessionId}`, { scroll: false });
      // Reset flag after navigation
      setTimeout(() => {
        isUpdatingUrl.current = false;
      }, 100);
    }
    // If session is cleared but URL has one, redirect to home
    else if (!sessionId && urlSessionId) {
      isUpdatingUrl.current = true;
      lastProcessedSessionId.current = null;
      router.push('/', { scroll: false });
      setTimeout(() => {
        isUpdatingUrl.current = false;
      }, 100);
    }
  }, [sessionId, params.sessionId, router, setSessionId]);

  // Mobile detection
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobileLocal(mobile);
      setIsMobile(mobile);

      // Auto-collapse sidebar on initial load if mobile
      if (mobile && sidebarOpen) {
        setSidebarOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Auto-collapse sidebar when switching to mobile
  useEffect(() => {
    if (isMobile && sidebarOpen) {
      setSidebarOpen(false);
    }
  }, [isMobile]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      const newWidth = Math.max(config.sidebar.minWidth, Math.min(config.sidebar.maxWidth, e.clientX));
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      isResizing.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, []);

  const handleKanbanMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizingKanban.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingKanban.current) return;
      const newWidth = Math.max(
        config.kanban.minWidth,
        Math.min(config.kanban.maxWidth, window.innerWidth - e.clientX)
      );
      setKanbanWidth(newWidth);
    };

    const handleMouseUp = () => {
      isResizingKanban.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, []);

  // Show loading while auth is checking
  if (isAuthLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Content area with sidebar and main */}
      <div className="flex flex-1 overflow-hidden">
        {/* Mobile backdrop */}
        {isMobile && sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {sidebarOpen && (
          <>
            <div
              className={`h-full shrink-0 border-r bg-background overflow-hidden ${
                isMobile
                  ? 'fixed inset-y-0 left-0 z-50 shadow-xl md:shadow-none max-h-screen'
                  : ''
              }`}
              style={{
                width: isMobile ? '280px' : sidebarWidth,
                maxHeight: isMobile ? '100dvh' : undefined
              }}
            >
              <SessionSidebar />
            </div>
            {/* Resizable handle - hidden on mobile */}
            {!isMobile && (
              <div
                className="h-full w-px shrink-0 cursor-col-resize bg-border hover:bg-primary/30 active:bg-primary/50 transition-colors flex items-center justify-center group relative"
                onMouseDown={handleMouseDown}
              >
                <div className="absolute h-8 w-4 rounded-sm border bg-muted flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm">
                  <GripVertical className="h-3 w-3 text-muted-foreground" />
                </div>
              </div>
            )}
          </>
        )}

        <main className="flex flex-col flex-1 overflow-hidden relative">
          <ChatHeader />
          <div className="flex flex-1 overflow-hidden">
            <div className="flex-1 overflow-hidden">
              {!agentId ? <AgentGrid /> : <ChatContainer />}
            </div>
            {/* Kanban Panel with resize handle */}
            {kanbanOpen && !isMobile && (
              <>
                {/* Resize handle */}
                <div
                  className="hidden md:flex h-full w-px shrink-0 cursor-col-resize bg-border hover:bg-primary/30 active:bg-primary/50 transition-colors items-center justify-center group relative"
                  onMouseDown={handleKanbanMouseDown}
                >
                  <div className="absolute h-8 w-4 rounded-sm border bg-muted flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm">
                    <GripVertical className="h-3 w-3 text-muted-foreground" />
                  </div>
                </div>
                <div
                  className="hidden md:block shrink-0 h-full overflow-hidden bg-background"
                  style={{ width: kanbanWidth }}
                >
                  <KanbanBoard panelWidth={kanbanWidth} />
                </div>
              </>
            )}
          </div>
        </main>
        {/* Mobile Kanban overlay */}
        {kanbanOpen && isMobile && (
          <>
            <div className="fixed inset-0 bg-black/50 z-[70] md:hidden" onClick={() => useKanbanStore.getState().setOpen(false)} />
            <div className="fixed inset-y-0 right-0 z-[80] w-[95vw] min-w-[280px] max-w-sm md:hidden shadow-xl bg-background">
              <KanbanBoard panelWidth={Math.min(window.innerWidth * 0.85, 384)} />
            </div>
          </>
        )}
      </div>

      {/* File Preview Modal */}
      <FilePreviewModal />
    </div>
  );
}
