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

const RESIZE_HANDLE_CLASS =
  'h-full w-px shrink-0 cursor-col-resize bg-border hover:bg-primary/30 active:bg-primary/50 transition-colors flex items-center justify-center group relative';

function readStoredWidth(key: string, min: number, max: number, fallback: number): number {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(key);
    if (saved) return Math.max(min, Math.min(max, parseInt(saved, 10)));
  }
  return fallback;
}

function ResizeGrip(): React.ReactElement {
  return (
    <div className="absolute h-8 w-4 rounded-sm border bg-muted flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm">
      <GripVertical className="h-3 w-3 text-muted-foreground" />
    </div>
  );
}

interface ResizePanelConfig {
  storageKey: string;
  min: number;
  max: number;
  defaultWidth: number;
  calcWidth: (clientX: number) => number;
}

function useResizePanel(
  panelConfig: ResizePanelConfig
): [number, React.Dispatch<React.SetStateAction<number>>, (e: React.MouseEvent) => void] {
  const { storageKey, min, max, defaultWidth, calcWidth } = panelConfig;
  const [width, setWidth] = useState<number>(() =>
    readStoredWidth(storageKey, min, max, defaultWidth)
  );
  const isResizing = useRef(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const onMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      setWidth(Math.max(min, Math.min(max, calcWidth(e.clientX))));
    };

    const onMouseUp = () => {
      isResizing.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, [min, max, calcWidth]);

  return [width, setWidth, handleMouseDown];
}

const sidebarPanelConfig: ResizePanelConfig = {
  storageKey: config.storage.sidebarWidth,
  min: config.sidebar.minWidth,
  max: config.sidebar.maxWidth,
  defaultWidth: config.sidebar.defaultWidth,
  calcWidth: (clientX: number) => clientX,
};

const kanbanPanelConfig: ResizePanelConfig = {
  storageKey: config.storage.kanbanWidth,
  min: config.kanban.minWidth,
  max: config.kanban.maxWidth,
  defaultWidth: config.kanban.defaultWidth,
  calcWidth: (clientX: number) => window.innerWidth - clientX,
};

export default function HomePage() {
  const { isLoading: isAuthLoading } = useAuth();
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

  const [sidebarWidth, , handleSidebarMouseDown] = useResizePanel(sidebarPanelConfig);
  const [kanbanWidth, , handleKanbanMouseDown] = useResizePanel(kanbanPanelConfig);

  const [isMobile, setIsMobileLocal] = useState(false);
  const isUpdatingUrl = useRef(false);
  const lastProcessedSessionId = useRef<string | null>(null);

  // Initialize agentId from localStorage ONLY on first mount
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    tokenService.fetchTokens().catch((err) => {
      console.error('Failed to obtain JWT tokens:', err);
    });

    const savedAgentId = localStorage.getItem(config.storage.selectedAgent);
    if (savedAgentId && !useChatStore.getState().agentId) {
      useChatStore.getState().setAgentId(savedAgentId);
    }
  }, []);

  // Persist sidebar width
  useEffect(() => {
    localStorage.setItem(config.storage.sidebarWidth, sidebarWidth.toString());
  }, [sidebarWidth]);

  // Persist kanban width
  useEffect(() => {
    localStorage.setItem(config.storage.kanbanWidth, kanbanWidth.toString());
  }, [kanbanWidth]);

  // Persist agentId (clear when null)
  useEffect(() => {
    if (agentId) {
      localStorage.setItem(config.storage.selectedAgent, agentId);
    } else {
      localStorage.removeItem(config.storage.selectedAgent);
    }
  }, [agentId]);

  // Sync session ID with URL
  useEffect(() => {
    if (isUpdatingUrl.current) return;

    const rawSessionId = params.sessionId;
    const urlSessionId = Array.isArray(rawSessionId) ? rawSessionId[0] : rawSessionId || null;

    if (urlSessionId === lastProcessedSessionId.current) return;

    function beginUrlUpdate(trackedId: string | null): void {
      isUpdatingUrl.current = true;
      lastProcessedSessionId.current = trackedId;
      setTimeout(() => { isUpdatingUrl.current = false; }, 100);
    }

    if (urlSessionId && urlSessionId !== sessionId) {
      beginUrlUpdate(urlSessionId);
      setSessionId(urlSessionId);
    } else if (sessionId && sessionId !== urlSessionId) {
      beginUrlUpdate(sessionId);
      router.push(`/s/${sessionId}`, { scroll: false });
    } else if (!sessionId && urlSessionId) {
      beginUrlUpdate(null);
      router.push('/', { scroll: false });
    }
  }, [sessionId, params.sessionId, router, setSessionId]);

  // Mobile detection
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobileLocal(mobile);
      setIsMobile(mobile);

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
            {!isMobile && (
              <div className={RESIZE_HANDLE_CLASS} onMouseDown={handleSidebarMouseDown}>
                <ResizeGrip />
              </div>
            )}
          </>
        )}

        <main className="flex flex-col flex-1 overflow-hidden relative">
          <ChatHeader />
          <div className="flex flex-1 overflow-hidden pt-[88px] md:pt-0">
            <div className="flex-1 overflow-hidden">
              {!agentId ? <AgentGrid /> : <ChatContainer />}
            </div>
            {kanbanOpen && !isMobile && (
              <>
                <div
                  className={`hidden md:flex ${RESIZE_HANDLE_CLASS}`}
                  onMouseDown={handleKanbanMouseDown}
                >
                  <ResizeGrip />
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

      <FilePreviewModal />
    </div>
  );
}
