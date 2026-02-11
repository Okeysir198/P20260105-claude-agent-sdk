import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  isMobile: boolean;
  sidebarActiveTab: 'sessions' | 'files';
  fileManagerOpen: boolean;

  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setIsMobile: (mobile: boolean) => void;
  setSidebarActiveTab: (tab: 'sessions' | 'files') => void;
  toggleFileManager: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      sidebarOpen: true,
      theme: 'system',
      isMobile: false,
      sidebarActiveTab: 'sessions',
      fileManagerOpen: false,

      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
      setIsMobile: (mobile) => set({ isMobile: mobile }),
      setSidebarActiveTab: (tab) => set({ sidebarActiveTab: tab }),
      toggleFileManager: () =>
        set((state) => ({ fileManagerOpen: !state.fileManagerOpen })),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        sidebarOpen: state.sidebarOpen,
        theme: state.theme,
        sidebarActiveTab: state.sidebarActiveTab,
      }),
    }
  )
);
