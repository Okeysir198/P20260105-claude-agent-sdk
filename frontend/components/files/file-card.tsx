'use client';

import { createElement, useState, useEffect } from 'react';
import { cn, relativeTime } from '@/lib/utils';
import { getFileIcon as getFileIconUtil, formatFileSize, isImageFile } from '@/lib/utils/file-utils';
import { Download, Trash2, Loader2, X, Check } from 'lucide-react';
import { API_URL } from '@/lib/constants';
import type { FileInfo } from '@/types';

interface FileCardProps {
  file: FileInfo;
  sessionId: string;
  onDownload: (file: FileInfo) => void;
  onDelete: (safeName: string) => void;
  isDownloading?: boolean;
  isDeleting?: boolean;
  /** When true, the card fades out before removal */
  isFadingOut?: boolean;
}

export function FileCard({
  file,
  sessionId,
  onDownload,
  onDelete,
  isDownloading = false,
  isDeleting = false,
  isFadingOut = false,
}: FileCardProps) {
  const FileIcon = getFileIconUtil(file.content_type, file.original_name);
  const isInput = file.file_type === 'input';
  const isBusy = isDownloading || isDeleting;
  const isImage = isImageFile(file.content_type, file.original_name);

  // Inline delete confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Reset confirmation on external state change
  useEffect(() => {
    if (!isDeleting) return;
    setShowDeleteConfirm(false);
  }, [isDeleting]);

  const handleDeleteClick = () => {
    if (showDeleteConfirm) {
      onDelete(file.safe_name);
      setShowDeleteConfirm(false);
    } else {
      setShowDeleteConfirm(true);
    }
  };

  const thumbnailUrl = isImage
    ? `${API_URL}/files/${encodeURIComponent(sessionId)}/download/${file.file_type}/${encodeURIComponent(file.safe_name)}`
    : null;

  return (
    <div
      className={cn(
        'group relative flex items-center gap-3',
        'bg-card border rounded-lg p-3 shadow-sm',
        'hover:shadow-md hover:border-primary/50',
        'transition-all duration-200',
        'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-1',
        isBusy && 'opacity-70',
        isFadingOut && 'opacity-0 scale-95 transition-all duration-300'
      )}
    >
      {/* File Icon / Thumbnail */}
      <div className="flex shrink-0 items-center justify-center w-9 h-9 rounded-md bg-muted/50 overflow-hidden">
        {thumbnailUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={thumbnailUrl}
            alt={file.original_name}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          createElement(FileIcon, {
            className: 'h-5 w-5 text-muted-foreground',
            'aria-hidden': 'true',
          })
        )}
      </div>

      {/* File Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p
            className="text-sm font-medium truncate text-foreground"
            title={file.original_name}
          >
            {file.original_name}
          </p>
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          {isDeleting ? (
            <span className="text-xs text-destructive flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Deleting…
            </span>
          ) : isDownloading ? (
            <span className="text-xs text-primary flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Downloading…
            </span>
          ) : (
            <>
              <span className="text-xs text-muted-foreground">
                {formatFileSize(file.size_bytes)}
              </span>
              <span className="text-xs text-muted-foreground/50">•</span>
              <span className="text-xs text-muted-foreground">
                {relativeTime(file.created_at)}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Type Badge */}
      <div
        className={cn(
          'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider',
          isInput
            ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'
            : 'bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20'
        )}
      >
        {file.file_type}
      </div>

      {/* Action Buttons */}
      <div
        className={cn(
          'flex items-center gap-1 transition-all duration-200',
          showDeleteConfirm ? 'opacity-100' : isBusy ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
        )}
      >
        {showDeleteConfirm ? (
          <>
            {/* Inline delete confirmation */}
            <span className="text-xs text-destructive mr-1 animate-in fade-in slide-in-from-right-2 duration-150">
              Delete?
            </span>
            <button
              type="button"
              onClick={handleDeleteClick}
              className={cn(
                'inline-flex items-center justify-center',
                'h-7 w-7 rounded-md',
                'bg-destructive/10 text-destructive hover:bg-destructive/20',
                'transition-colors animate-in fade-in duration-150'
              )}
              title="Confirm delete"
              aria-label={`Confirm delete ${file.original_name}`}
            >
              <Check className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setShowDeleteConfirm(false)}
              className={cn(
                'inline-flex items-center justify-center',
                'h-7 w-7 rounded-md',
                'hover:bg-accent text-muted-foreground',
                'transition-colors animate-in fade-in duration-150'
              )}
              title="Cancel"
              aria-label="Cancel delete"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              onClick={() => onDownload(file)}
              disabled={isBusy}
              className={cn(
                'inline-flex items-center justify-center',
                'h-7 w-7 rounded-md',
                'hover:bg-accent hover:text-accent-foreground',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                'transition-colors',
                'text-muted-foreground',
                isBusy && 'pointer-events-none'
              )}
              title="Download file"
              aria-label={`Download ${file.original_name}`}
            >
              {isDownloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
              ) : (
                <Download className="h-3.5 w-3.5" />
              )}
            </button>

            <button
              type="button"
              onClick={handleDeleteClick}
              disabled={isBusy}
              className={cn(
                'inline-flex items-center justify-center',
                'h-7 w-7 rounded-md',
                'hover:bg-destructive/10 hover:text-destructive',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                'transition-colors',
                'text-muted-foreground',
                isBusy && 'pointer-events-none'
              )}
              title="Delete file"
              aria-label={`Delete ${file.original_name}`}
            >
              {isDeleting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-destructive" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
