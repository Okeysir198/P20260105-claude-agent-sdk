'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  UploadCloud,
  FilePlus,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  RotateCw,
  FileIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatFileSize } from '@/lib/utils/file-utils';
import type { UploadQueueItem } from '@/lib/store/file-store';

interface UploadZoneProps {
  onUpload: (files: File[]) => void;
  isUploading?: boolean;
  uploadQueue?: Map<string, UploadQueueItem>;
  onRetry?: (id: string) => void;
  onDismiss?: (id: string) => void;
}

export function UploadZone({
  onUpload,
  isUploading = false,
  uploadQueue = new Map(),
  onRetry,
  onDismiss,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      setIsDragging(false);
      if (acceptedFiles.length > 0 && !isUploading) {
        onUpload(acceptedFiles);
      }
    },
    [onUpload, isUploading]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDragEnter: () => setIsDragging(true),
    onDragLeave: () => setIsDragging(false),
    noClick: isUploading,
    multiple: true,
  });

  const queueEntries = Array.from(uploadQueue.entries());
  const hasQueue = queueEntries.length > 0;
  const activeUploads = queueEntries.filter(
    ([, item]) => item.status === 'uploading' || item.status === 'pending'
  );
  const hasActiveUploads = activeUploads.length > 0;

  return (
    <div className="space-y-2">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={cn(
          'relative flex items-center justify-center rounded-lg border-2 border-dashed transition-all duration-200 cursor-pointer',
          'hover:border-primary hover:bg-primary/5',
          isDragActive
            ? 'border-primary bg-primary/10 py-6'
            : 'border-border py-3 px-4',
          isUploading && 'opacity-60 cursor-not-allowed'
        )}
      >
        <input {...getInputProps()} disabled={isUploading} />

        {isDragActive ? (
          <div className="flex flex-col items-center gap-2">
            <FilePlus className="h-6 w-6 text-primary" />
            <p className="text-sm font-medium text-foreground">Drop files to upload</p>
            <p className="text-xs text-muted-foreground">
              PDF, DOC, XLS, Images, Code, Archives
            </p>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            {hasActiveUploads ? (
              <Loader2 className="h-4 w-4 text-primary animate-spin shrink-0" />
            ) : (
              <UploadCloud className="h-4 w-4 text-muted-foreground shrink-0" />
            )}
            <span className="text-xs text-muted-foreground">
              {hasActiveUploads
                ? `Uploading ${activeUploads.length} file${activeUploads.length > 1 ? 's' : ''}…`
                : 'Drop files or click to upload'}
            </span>
          </div>
        )}
      </div>

      {/* Upload queue items */}
      {hasQueue && (
        <div className="space-y-1.5">
          {queueEntries.map(([id, item]) => (
            <UploadQueueRow
              key={id}
              id={id}
              item={item}
              onRetry={onRetry}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function UploadQueueRow({
  id,
  item,
  onRetry,
  onDismiss,
}: {
  id: string;
  item: UploadQueueItem;
  onRetry?: (id: string) => void;
  onDismiss?: (id: string) => void;
}) {
  const isComplete = item.status === 'done';
  const isError = item.status === 'error';
  const isActive = item.status === 'uploading' || item.status === 'pending';

  return (
    <div
      className={cn(
        'flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs animate-in fade-in slide-in-from-top-1 duration-200',
        isError && 'border-destructive/30 bg-destructive/5',
        isComplete && 'border-green-500/30 bg-green-500/5',
        isActive && 'border-border bg-card'
      )}
    >
      {/* Icon */}
      <div className="shrink-0">
        {isError ? (
          <AlertCircle className="h-3.5 w-3.5 text-destructive" />
        ) : isComplete ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
        ) : (
          <FileIcon className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </div>

      {/* File info + progress */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-foreground" title={item.file.name}>
            {item.file.name}
          </span>
          <span className="shrink-0 text-muted-foreground">
            {formatFileSize(item.file.size)}
          </span>
        </div>
        {isActive && (
          <div className="mt-1 h-1 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${item.progress}%` }}
            />
          </div>
        )}
        {isError && item.error && (
          <p className="mt-0.5 text-destructive truncate" title={item.error}>
            {item.error}
          </p>
        )}
      </div>

      {/* Status / Actions */}
      <div className="shrink-0 flex items-center gap-1">
        {isActive && (
          <span className="text-primary font-medium">{item.progress}%</span>
        )}
        {isError && onRetry && (
          <button
            type="button"
            onClick={() => onRetry(id)}
            className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="Retry upload"
          >
            <RotateCw className="h-3 w-3" />
          </button>
        )}
        {(isError || isComplete) && onDismiss && (
          <button
            type="button"
            onClick={() => onDismiss(id)}
            className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="Dismiss"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}
