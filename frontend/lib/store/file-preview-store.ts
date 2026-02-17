import { create } from 'zustand';
import type { FileInfo } from '@/types';

interface FilePreviewStore {
  isOpen: boolean;
  file: FileInfo | null;
  sessionId: string | null;
  openPreview: (file: FileInfo, sessionId: string) => void;
  closePreview: () => void;
}

export const useFilePreviewStore = create<FilePreviewStore>((set) => ({
  isOpen: false,
  file: null,
  sessionId: null,
  openPreview: (file, sessionId) => set({ isOpen: true, file, sessionId }),
  closePreview: () => set({ isOpen: false, file: null, sessionId: null }),
}));
