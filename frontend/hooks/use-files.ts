'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { QUERY_KEYS } from '@/lib/constants';
import { toast } from 'sonner';
import type { FileInfo } from '@/types';

/**
 * Hook for listing files in a session.
 * Auto-refetches on mount and on file upload/delete events.
 *
 * @param sessionId - Session identifier
 * @param fileType - Optional file type filter ('input' or 'output')
 * @returns Query result with files, loading state, error, and refetch function
 */
export function useFiles(sessionId: string, fileType?: 'input' | 'output') {
  return useQuery({
    queryKey: [QUERY_KEYS.FILES, sessionId, fileType],
    queryFn: () => apiClient.listFiles(sessionId, fileType),
    enabled: !!sessionId,
    refetchOnWindowFocus: true,
    retry: 1,
  });
}

/**
 * Hook for uploading files to a session.
 * Provides upload progress tracking and toast notifications.
 *
 * @param sessionId - Session identifier
 * @returns Mutation with uploadFile function, uploading state, and progress
 */
export function useFileUpload(sessionId: string) {
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
      });
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

/**
 * Hook for deleting files from a session.
 * Provides toast notifications on success/error.
 *
 * @param sessionId - Session identifier
 * @returns Mutation with deleteFile function and deleting state
 */
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

/**
 * Hook for downloading files from a session.
 *
 * @param sessionId - Session identifier
 * @returns Object with downloadFile function and downloading state
 */
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

/**
 * Combined hook for complete file management in a session.
 * Provides all file operations in a single hook.
 *
 * @param sessionId - Session identifier
 * @param fileType - Optional file type filter
 * @returns Object with files list and all file operations
 */
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

/**
 * Hook for fetching and caching file content.
 * Returns text content for text-based files, blob for binary files.
 *
 * @param sessionId - Session identifier
 * @param file - File info object
 * @returns Query result with file content (string | Blob | null)
 */
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
