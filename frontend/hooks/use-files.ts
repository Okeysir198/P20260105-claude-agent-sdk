'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { QUERY_KEYS } from '@/lib/constants';
import { toast } from 'sonner';
import type { FileInfo } from '@/types';

/** Lists files in a session, auto-refetching on window focus. */
export function useFiles(sessionId: string, fileType?: 'input' | 'output') {
  return useQuery({
    queryKey: [QUERY_KEYS.FILES, sessionId, fileType],
    queryFn: () => apiClient.listFiles(sessionId, fileType),
    enabled: !!sessionId,
    refetchOnWindowFocus: true,
    retry: 1,
  });
}

/** Uploads files to a session with progress tracking and toast notifications. */
export function useFileUpload(sessionId: string, cwdId?: string) {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);

  const uploadMutation = useMutation({
    mutationFn: async ({
      file,
      onProgress,
    }: {
      file: File;
      onProgress?: (progress: number) => void;
    }) => {
      setProgress(0);
      return apiClient.uploadFile(sessionId, file, (prog) => {
        setProgress(prog);
        onProgress?.(prog);
      }, cwdId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.FILES, sessionId],
      });
      toast.success('File uploaded successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to upload file');
    },
    onSettled: () => {
      setProgress(0);
    },
  });

  return {
    uploadFile: uploadMutation.mutateAsync,
    isUploading: uploadMutation.isPending,
    progress,
  };
}

/** Deletes files from a session with toast notifications. */
export function useFileDelete(sessionId: string) {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: async ({
      safeName,
      fileType,
    }: {
      safeName: string;
      fileType: 'input' | 'output';
    }) => {
      return apiClient.deleteFile(sessionId, safeName, fileType);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.FILES, sessionId],
      });
      toast.success('File deleted successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete file');
    },
  });

  return {
    deleteFile: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
  };
}

/** Downloads files from a session via browser-triggered blob download. */
export function useFileDownload(sessionId: string) {
  const [isDownloading, setIsDownloading] = useState(false);

  const downloadFile = useCallback(
    async (fileType: 'input' | 'output', safeName: string, originalName?: string) => {
      setIsDownloading(true);
      try {
        const blob = await apiClient.downloadFile(sessionId, fileType, safeName);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = originalName || safeName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Failed to download file');
        throw error;
      } finally {
        setIsDownloading(false);
      }
    },
    [sessionId]
  );

  return {
    downloadFile,
    isDownloading,
  };
}

/** Combined hook providing all file operations (list, upload, delete, download) for a session. */
export function useFileOperations(
  sessionId: string,
  fileType?: 'input' | 'output'
) {
  const filesQuery = useFiles(sessionId, fileType);
  const upload = useFileUpload(sessionId);
  const deleteOperation = useFileDelete(sessionId);
  const download = useFileDownload(sessionId);

  return {
    files: filesQuery.data?.files ?? [],
    isLoadingFiles: filesQuery.isLoading,
    filesError: filesQuery.error,
    refetchFiles: filesQuery.refetch,
    uploadFile: upload.uploadFile,
    isUploading: upload.isUploading,
    uploadProgress: upload.progress,
    deleteFile: deleteOperation.deleteFile,
    isDeleting: deleteOperation.isDeleting,
    downloadFile: download.downloadFile,
    isDownloading: download.isDownloading,
  };
}

/** Fetches and caches file content. Returns text for text files, Blob for binary. */
export function useFileContent(sessionId: string, file: FileInfo | null) {
  return useQuery({
    queryKey: ['file-content', sessionId, file?.file_type, file?.safe_name],
    queryFn: async () => {
      if (!file) return null;

      const blob = await apiClient.downloadFile(sessionId, file.file_type, file.safe_name);

      // Return text for text-based files, blob for binary
      if (file.content_type?.startsWith('text/') || file.content_type?.includes('json')) {
        return await blob.text();
      }
      return blob;
    },
    enabled: !!file && !!sessionId,
    staleTime: 5 * 60 * 1000, // 5 min cache
  });
}
