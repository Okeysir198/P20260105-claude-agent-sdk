'use client';

import { useState, useCallback, useRef } from 'react';
import { useFileOperations } from '@/hooks/use-files';
import { ScrollArea } from '@/components/ui/scroll-area';
import { UploadZone } from './upload-zone';
import { FileCard } from './file-card';
import { FolderOpen } from 'lucide-react';
import { useFileStore } from '@/lib/store/file-store';
import type { FileInfo } from '@/types';
import { formatFileSize } from '@/lib/utils/file-utils';
import { toast } from 'sonner';

interface FileManagerContentProps {
  sessionId: string;
}

export function FileManagerContent({ sessionId }: FileManagerContentProps) {
  const {
    files,
    isLoadingFiles,
    uploadFile,
    isUploading,
    deleteFile,
    downloadFile,
    refetchFiles,
  } = useFileOperations(sessionId);

  // Per-file action tracking
  const [deletingFiles, setDeletingFiles] = useState<Set<string>>(new Set());
  const [fadingFiles, setFadingFiles] = useState<Set<string>>(new Set());
  const [downloadingFiles, setDownloadingFiles] = useState<Set<string>>(new Set());

  // Upload queue from store
  const uploadQueue = useFileStore((s) => s.uploadQueue);
  const addToQueue = useFileStore((s) => s.addToQueue);
  const updateQueueItem = useFileStore((s) => s.updateQueueItem);
  const removeFromQueue = useFileStore((s) => s.removeFromQueue);

  // Counter for unique queue IDs
  const queueIdRef = useRef(0);

  const uploadSingleFile = useCallback(
    async (id: string, file: File) => {
      updateQueueItem(id, { status: 'uploading', progress: 0, error: undefined });
      try {
        await uploadFile({
          file,
          onProgress: (prog: number) => {
            updateQueueItem(id, { progress: prog });
          },
        });
        updateQueueItem(id, { status: 'done', progress: 100 });
        // Auto-dismiss after delay
        setTimeout(() => removeFromQueue(id), 2000);
        return true;
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Upload failed';
        updateQueueItem(id, { status: 'error', error: message });
        return false;
      }
    },
    [uploadFile, updateQueueItem, removeFromQueue]
  );

  const handleUpload = useCallback(
    async (filesToUpload: File[]) => {
      if (filesToUpload.length === 0) return;

      // Add all files to queue
      const entries: Array<{ id: string; file: File }> = [];
      for (const file of filesToUpload) {
        const id = `upload-${++queueIdRef.current}`;
        addToQueue(id, file);
        entries.push({ id, file });
      }

      // Upload in parallel
      const results = await Promise.allSettled(
        entries.map(({ id, file }) => uploadSingleFile(id, file))
      );

      const succeeded = results.filter(
        (r) => r.status === 'fulfilled' && r.value === true
      ).length;
      const failed = filesToUpload.length - succeeded;

      if (filesToUpload.length > 1) {
        if (failed === 0) {
          toast.success(`${succeeded} file${succeeded > 1 ? 's' : ''} uploaded`);
        } else {
          toast.warning(`${succeeded} of ${filesToUpload.length} files uploaded, ${failed} failed`);
        }
      }
    },
    [addToQueue, uploadSingleFile]
  );

  const handleRetry = useCallback(
    (id: string) => {
      const item = uploadQueue.get(id);
      if (item) {
        uploadSingleFile(id, item.file);
      }
    },
    [uploadQueue, uploadSingleFile]
  );

  const handleDismiss = useCallback(
    (id: string) => removeFromQueue(id),
    [removeFromQueue]
  );

  const handleDelete = useCallback(
    async (safeName: string, fileType: 'input' | 'output') => {
      // Optimistic: fade out immediately
      setFadingFiles((prev) => new Set(prev).add(safeName));

      // Wait for fade animation
      await new Promise((resolve) => setTimeout(resolve, 300));

      setDeletingFiles((prev) => new Set(prev).add(safeName));
      try {
        await deleteFile({ safeName, fileType });
      } catch (error) {
        // Re-add on failure: clear fading state + refetch
        console.error('Delete failed:', error);
        await refetchFiles();
      } finally {
        setDeletingFiles((prev) => {
          const next = new Set(prev);
          next.delete(safeName);
          return next;
        });
        setFadingFiles((prev) => {
          const next = new Set(prev);
          next.delete(safeName);
          return next;
        });
      }
    },
    [deleteFile, refetchFiles]
  );

  const handleDownload = useCallback(
    async (file: FileInfo) => {
      setDownloadingFiles((prev) => new Set(prev).add(file.safe_name));
      try {
        await downloadFile(file.file_type, file.safe_name, file.original_name);
      } catch (error) {
        console.error('Download failed:', error);
      } finally {
        setDownloadingFiles((prev) => {
          const next = new Set(prev);
          next.delete(file.safe_name);
          return next;
        });
      }
    },
    [downloadFile]
  );

  // Calculate total size
  const totalSizeBytes = files.reduce((sum, file) => sum + file.size_bytes, 0);
  const totalSizeFormatted = formatFileSize(totalSizeBytes);

  return (
    <div className="flex flex-col h-full">
      {/* Upload zone at top */}
      <UploadZone
        onUpload={handleUpload}
        isUploading={isUploading}
        uploadQueue={uploadQueue}
        onRetry={handleRetry}
        onDismiss={handleDismiss}
      />

      {/* File list */}
      <ScrollArea className="flex-1 mt-2">
        <div className="px-2 pb-2 space-y-1">
          {isLoadingFiles ? (
            <div className="space-y-2 py-2">
              {/* Skeleton loading */}
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 rounded-md border p-2 animate-pulse"
                >
                  <div className="w-8 h-8 rounded bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3 w-28 bg-muted rounded" />
                    <div className="h-2.5 w-16 bg-muted rounded" />
                  </div>
                  <div className="h-5 w-12 bg-muted rounded" />
                </div>
              ))}
            </div>
          ) : files.length > 0 ? (
            files.map((file) => (
              <FileCard
                key={`${file.file_type}-${file.safe_name}`}
                file={file}
                sessionId={sessionId}
                onDownload={handleDownload}
                onDelete={() => handleDelete(file.safe_name, file.file_type)}
                isDownloading={downloadingFiles.has(file.safe_name)}
                isDeleting={deletingFiles.has(file.safe_name)}
                isFadingOut={fadingFiles.has(file.safe_name)}
              />
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center mb-2">
                <FolderOpen className="h-5 w-5 text-muted-foreground" />
              </div>
              <p className="text-sm text-muted-foreground font-medium">No files yet</p>
              <p className="text-xs text-muted-foreground mt-1">Upload files to get started!</p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer with stats */}
      <div className="flex-shrink-0 border-t px-3 py-2 bg-muted/30">
        <p className="text-[10px] text-muted-foreground">
          {files.length} {files.length === 1 ? 'file' : 'files'} • {totalSizeFormatted} used
        </p>
      </div>
    </div>
  );
}
