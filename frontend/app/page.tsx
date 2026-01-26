'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useUIStore } from '@/lib/store/ui-store';
import { AgentGrid } from '@/components/agent/agent-grid';
import { ChatContainer } from '@/components/chat/chat-container';
import { ChatHeader } from '@/components/chat/chat-header';
import { SessionSidebar } from '@/components/session/session-sidebar';
import { GripVertical } from 'lucide-react';
import { tokenService } from '@/lib/auth';

export default function HomePage() {
  const agentId = useChatStore((s) => s.agentId);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const setIsMobile = useUIStore((s) => s.setIsMobile);
  const hasInitialized = useRef(false);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [isMobile, setIsMobileLocal] = useState(false);
  const isResizing = useRef(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  // Initialize agentId from localStorage ONLY on first mount
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    // Fetch fresh JWT tokens on page load via proxy
    const initializeTokens = async () => {
      setIsCheckingAuth(true);
      try {
        await tokenService.fetchTokens();
        setIsAuthenticated(true);
      } catch (err) {
        console.error('Failed to obtain JWT tokens:', err);
        setIsAuthenticated(false);
      } finally {
        setIsCheckingAuth(false);
      }
    };

    initializeTokens();

    const savedAgentId = localStorage.getItem('claude-chat-selected-agent');
    if (savedAgentId && !useChatStore.getState().agentId) {
      useChatStore.getState().setAgentId(savedAgentId);
    }

    // Load saved sidebar width
    const savedWidth = localStorage.getItem('sidebar-width');
    if (savedWidth) {
      setSidebarWidth(Math.max(240, Math.min(500, parseInt(savedWidth, 10))));
    }
  }, []);

  // Save sidebar width to localStorage
  useEffect(() => {
    localStorage.setItem('sidebar-width', sidebarWidth.toString());
  }, [sidebarWidth]);

  // Save agentId to localStorage when it changes (clear when null)
  useEffect(() => {
    if (agentId) {
      localStorage.setItem('claude-chat-selected-agent', agentId);
    } else {
      localStorage.removeItem('claude-chat-selected-agent');
    }
  }, [agentId]);

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
      const newWidth = Math.max(240, Math.min(500, e.clientX));
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

  // Show loading while checking auth
  if (isCheckingAuth) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-red-500">Authentication failed. Please check your API key configuration.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
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
            className={`h-full shrink-0 border-r bg-background ${
              isMobile
                ? 'fixed inset-y-0 left-0 z-50 shadow-xl md:shadow-none'
                : ''
            }`}
            style={{
              width: isMobile ? '280px' : sidebarWidth,
              ...(isMobile ? {} : {})
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
      <main className="flex flex-col flex-1 h-full overflow-hidden">
        <ChatHeader />
        <div className="flex-1 overflow-hidden">
          {!agentId ? <AgentGrid /> : <ChatContainer />}
        </div>
      </main>
    </div>
  );
}
