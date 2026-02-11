import { create } from 'zustand';
import type { FileMetadata } from '@/types';

interface FileState {
  files: FileMetadata[];
  isLoading: boolean;
  error: string | null;
  uploadProgress: Map<string, number>;

  setFiles: (files: FileMetadata[]) => void;
  addFile: (file: FileMetadata) => void;
  removeFile: (safeName: string) => void;
  updateUploadProgress: (filename: string, progress: number) => void;
  clearUploadProgress: (filename: string) => void;
  clear: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useFileStore = create<FileState>((set, get) => ({
  files: [],
  isLoading: false,
  error: null,
  uploadProgress: new Map(),

  setFiles: (files) => set({ files }),

  addFile: (file) =>
    set((state) => ({
      files: [...state.files, file],
    })),

  removeFile: (safeName) =>
    set((state) => ({
      files: state.files.filter((f) => f.safe_name !== safeName),
    })),

  updateUploadProgress: (filename, progress) =>
    set((state) => {
      const newProgress = new Map(state.uploadProgress);
      newProgress.set(filename, progress);
      return { uploadProgress: newProgress };
    }),

  clearUploadProgress: (filename) =>
    set((state) => {
      const newProgress = new Map(state.uploadProgress);
      newProgress.delete(filename);
      return { uploadProgress: newProgress };
    }),

  clear: () =>
    set({
      files: [],
      isLoading: false,
      error: null,
      uploadProgress: new Map(),
    }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),
}));
