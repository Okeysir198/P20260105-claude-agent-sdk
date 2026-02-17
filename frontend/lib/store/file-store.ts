import { create } from 'zustand';

export type UploadStatus = 'pending' | 'uploading' | 'done' | 'error';

export interface UploadQueueItem {
  file: File;
  progress: number;
  status: UploadStatus;
  error?: string;
}

interface FileState {
  uploadQueue: Map<string, UploadQueueItem>;

  addToQueue: (id: string, file: File) => void;
  updateQueueItem: (id: string, update: Partial<UploadQueueItem>) => void;
  removeFromQueue: (id: string) => void;
}

export const useFileStore = create<FileState>((set) => ({
  uploadQueue: new Map(),

  addToQueue: (id, file) =>
    set((state) => {
      const next = new Map(state.uploadQueue);
      next.set(id, { file, progress: 0, status: 'pending' });
      return { uploadQueue: next };
    }),

  updateQueueItem: (id, update) =>
    set((state) => {
      const next = new Map(state.uploadQueue);
      const existing = next.get(id);
      if (existing) {
        next.set(id, { ...existing, ...update });
      }
      return { uploadQueue: next };
    }),

  removeFromQueue: (id) =>
    set((state) => {
      const next = new Map(state.uploadQueue);
      next.delete(id);
      return { uploadQueue: next };
    }),
}));
