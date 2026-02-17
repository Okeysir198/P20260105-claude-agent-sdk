'use client';

import { createElement, useState, useEffect, useRef } from 'react';
import { cn, relativeTime } from '@/lib/utils';
import { getFileIcon as getFileIconUtil, formatFileSize, isImageFile } from '@/lib/utils/file-utils';
import { Download, Trash2, Loader2, X, Check, MoreVertical } from 'lucide-react';
import { API_URL } from '@/lib/constants';
import type { FileInfo } from '@/types';
import { useFilePreviewStore } from '@/lib/store/file-preview-store';

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
  const openPreview = useFilePreviewStore((s) => s.openPreview);

  // Get icon-specific color based on file type
  const getFileIconColor = (): string => {
    if (file.content_type?.startsWith('image/')) return 'text-purple-500 dark:text-purple-400';
    if (file.content_type?.startsWith('video/')) return 'text-pink-500 dark:text-pink-400';
    if (file.content_type?.startsWith('audio/')) return 'text-orange-500 dark:text-orange-400';
    if (file.content_type?.includes('pdf')) return 'text-red-500 dark:text-red-400';
    if (file.content_type?.includes('sheet') || file.content_type?.includes('excel')) return 'text-emerald-500 dark:text-emerald-400';
    if (file.content_type?.includes('word') || file.content_type?.includes('document')) return 'text-blue-500 dark:text-blue-400';
    if (file.content_type?.includes('zip') || file.content_type?.includes('rar') || file.content_type?.includes('tar')) return 'text-amber-500 dark:text-amber-400';
    if (file.content_type?.includes('json')) return 'text-yellow-500 dark:text-yellow-400';
    if (file.content_type?.includes('javascript') || file.content_type?.includes('python') || file.content_type?.includes('java')) return 'text-cyan-500 dark:text-cyan-400';
    if (file.original_name) {
      const ext = file.original_name.split('.').pop()?.toLowerCase();
      const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'];
      const codeExts = ['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 'go', 'rs', 'rb', 'php', 'swift', 'kt'];
      const docExts = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'];
      const sheetExts = ['xls', 'xlsx', 'csv', 'ods'];
      const archiveExts = ['zip', 'rar', '7z', 'tar', 'gz'];
      if (imageExts.includes(ext!)) return 'text-purple-500 dark:text-purple-400';
      if (codeExts.includes(ext!)) return 'text-cyan-500 dark:text-cyan-400';
      if (docExts.includes(ext!)) {
        if (ext === 'pdf') return 'text-red-500 dark:text-red-400';
        return 'text-blue-500 dark:text-blue-400';
      }
      if (sheetExts.includes(ext!)) return 'text-emerald-500 dark:text-emerald-400';
      if (archiveExts.includes(ext!)) return 'text-amber-500 dark:text-amber-400';
    }
    return 'text-muted-foreground';
  };

  const getIconBgColor = (): string => {
    if (file.content_type?.startsWith('image/')) return 'bg-purple-500/10 dark:bg-purple-500/5';
    if (file.content_type?.startsWith('video/')) return 'bg-pink-500/10 dark:bg-pink-500/5';
    if (file.content_type?.startsWith('audio/')) return 'bg-orange-500/10 dark:bg-orange-500/5';
    if (file.content_type?.includes('pdf')) return 'bg-red-500/10 dark:bg-red-500/5';
    if (file.content_type?.includes('sheet') || file.content_type?.includes('excel')) return 'bg-emerald-500/10 dark:bg-emerald-500/5';
    if (file.content_type?.includes('word') || file.content_type?.includes('document')) return 'bg-blue-500/10 dark:bg-blue-500/5';
    if (file.content_type?.includes('zip') || file.content_type?.includes('rar') || file.content_type?.includes('tar')) return 'bg-amber-500/10 dark:bg-amber-500/5';
    if (file.content_type?.includes('json')) return 'bg-yellow-500/10 dark:bg-yellow-500/5';
    if (file.content_type?.includes('javascript') || file.content_type?.includes('python') || file.content_type?.includes('java')) return 'bg-cyan-500/10 dark:bg-cyan-500/5';
    if (file.original_name) {
      const ext = file.original_name.split('.').pop()?.toLowerCase();
      const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'];
      const codeExts = ['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 'go', 'rs', 'rb', 'php', 'swift', 'kt'];
      const docExts = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'];
      const sheetExts = ['xls', 'xlsx', 'csv', 'ods'];
      const archiveExts = ['zip', 'rar', '7z', 'tar', 'gz'];
      if (imageExts.includes(ext!)) return 'bg-purple-500/10 dark:bg-purple-500/5';
      if (codeExts.includes(ext!)) return 'bg-cyan-500/10 dark:bg-cyan-500/5';
      if (docExts.includes(ext!)) {
        if (ext === 'pdf') return 'bg-red-500/10 dark:bg-red-500/5';
        return 'bg-blue-500/10 dark:bg-blue-500/5';
      }
      if (sheetExts.includes(ext!)) return 'bg-emerald-500/10 dark:bg-emerald-500/5';
      if (archiveExts.includes(ext!)) return 'bg-amber-500/10 dark:bg-amber-500/5';
    }
    return 'bg-muted/60';
  };

  // Inline delete confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Reset confirmation on external state change
  useEffect(() => {
    if (!isDeleting) return;
    setShowDeleteConfirm(false);
  }, [isDeleting]);

  // Close menu when clicking outside
  useEffect(() => {
    if (!showMenu) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
        setShowDeleteConfirm(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showMenu]);

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

  const handleCardClick = (e: React.MouseEvent | React.KeyboardEvent) => {
    // Prevent opening preview if clicking on menu or its children
    const target = e.target as HTMLElement;
    if (target.closest('[data-menu-trigger]')) {
      return;
    }
    openPreview(file, sessionId);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleCardClick(e);
    }
  };

  return (
    <div
      className={cn(
        'group relative flex items-center gap-3 sm:gap-4',
        'bg-card border rounded-xl p-2.5 pr-3 shadow-sm',
        'hover:shadow-md hover:border-primary/40',
        'transition-all duration-200 ease-out',
        'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
        'cursor-pointer',
        isBusy && 'opacity-70',
        isFadingOut && 'opacity-0 scale-95 transition-all duration-300'
      )}
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`Preview ${file.original_name}`}
    >
      {/* File Icon / Thumbnail */}
      <div
        className={cn(
          'flex shrink-0 items-center justify-center w-10 h-10 lg:w-11 lg:h-11 rounded-lg overflow-hidden shadow-sm border border-border/40',
          getIconBgColor()
        )}
      >
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
            className: cn('h-5 w-5 lg:h-5.5 lg:w-5.5', getFileIconColor()),
            'aria-hidden': 'true',
          })
        )}
      </div>

      {/* File Info */}
      <div className="min-w-0 flex-1 min-h-[40px] flex flex-col justify-center">
        <div className="flex items-center gap-2 mb-0.5">
          <p
            className="text-sm font-semibold truncate text-foreground"
            title={file.original_name}
          >
            {file.original_name}
          </p>
          {/* Type Badge - Inline with filename */}
          <span
            className={cn(
              'inline-flex items-center px-1.5 py-0.5 rounded-full',
              'text-[9px] lg:text-[10px] font-medium uppercase tracking-wide shrink-0',
              isInput
                ? 'bg-blue-500/8 text-blue-600 dark:text-blue-400 border border-blue-500/12'
                : 'bg-emerald-500/8 text-emerald-600 dark:text-emerald-400 border border-emerald-500/12'
            )}
          >
            {file.file_type}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {isDeleting ? (
            <span className="text-xs text-destructive font-medium flex items-center gap-1.5">
              <Loader2 className="h-3 w-3 animate-spin" />
              Deleting…
            </span>
          ) : isDownloading ? (
            <span className="text-xs text-primary font-medium flex items-center gap-1.5">
              <Loader2 className="h-3 w-3 animate-spin" />
              Downloading…
            </span>
          ) : (
            <>
              <span className="text-xs text-muted-foreground">
                {formatFileSize(file.size_bytes)}
              </span>
              <span className="text-xs text-muted-foreground/30">•</span>
              <span className="text-xs text-muted-foreground">
                {relativeTime(file.created_at)}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Action Menu - Shows on hover */}
      <div className="relative shrink-0 ml-auto" ref={menuRef} data-menu-trigger>
        {showDeleteConfirm ? (
          <div className="flex items-center gap-1.5 animate-in fade-in slide-in-from-right-2 duration-150">
            <span className="text-xs text-destructive font-medium mr-1 hidden sm:inline-flex">
              Delete?
            </span>
            <button
              type="button"
              onClick={handleDeleteClick}
              className={cn(
                'inline-flex items-center justify-center',
                'h-8 w-8 rounded-lg',
                'bg-destructive text-destructive-foreground hover:bg-destructive/90',
                'focus:outline-none focus:ring-2 focus:ring-destructive focus:ring-offset-2',
                'transition-all duration-150',
                'font-medium'
              )}
              title="Confirm delete"
              aria-label={`Confirm delete ${file.original_name}`}
            >
              <Check className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => {
                setShowDeleteConfirm(false);
                setShowMenu(false);
              }}
              className={cn(
                'inline-flex items-center justify-center',
                'h-8 w-8 rounded-lg',
                'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
                'transition-all duration-150'
              )}
              title="Cancel"
              aria-label="Cancel delete"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <>
            {/* More button - Shows on hover */}
            <button
              type="button"
              onClick={() => setShowMenu(!showMenu)}
              disabled={isBusy}
              className={cn(
                'inline-flex items-center justify-center',
                'h-8 w-8 rounded-lg',
                'text-muted-foreground hover:text-foreground',
                'hover:bg-accent/80 active:bg-accent',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
                'transition-all duration-150',
                'opacity-0 group-hover:opacity-100',
                'disabled:opacity-50 disabled:pointer-events-none',
                showMenu && 'opacity-100',
                isBusy && 'pointer-events-none'
              )}
              title="More options"
              aria-label={`More options for ${file.original_name}`}
            >
              <MoreVertical className="h-4 w-4" />
            </button>

            {/* Dropdown Menu */}
            {showMenu && (
              <div
                className={cn(
                  'absolute right-0 top-10 z-50',
                  'min-w-[160px] rounded-lg border bg-popover shadow-md',
                  'p-1 space-y-0.5',
                  'animate-in fade-in slide-in-from-top-1 duration-150'
                )}
              >
                <button
                  type="button"
                  onClick={() => {
                    onDownload(file);
                    setShowMenu(false);
                  }}
                  disabled={isBusy}
                  className={cn(
                    'w-full flex items-center gap-2 px-2 py-2 rounded-md',
                    'text-xs text-left',
                    'hover:bg-accent hover:text-accent-foreground',
                    'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-inset',
                    'transition-colors',
                    'disabled:opacity-50 disabled:pointer-events-none',
                    isBusy && 'pointer-events-none'
                  )}
                >
                  {isDownloading ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary shrink-0" />
                      <span className="font-medium">Downloading…</span>
                    </>
                  ) : (
                    <>
                      <Download className="h-3.5 w-3.5 shrink-0" />
                      <span>Download</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setShowDeleteConfirm(true);
                  }}
                  disabled={isBusy}
                  className={cn(
                    'w-full flex items-center gap-2 px-2 py-2 rounded-md',
                    'text-xs text-left text-destructive hover:text-destructive',
                    'hover:bg-destructive/8',
                    'focus:outline-none focus:ring-2 focus:ring-destructive focus:ring-inset',
                    'transition-colors',
                    'disabled:opacity-50 disabled:pointer-events-none',
                    isBusy && 'pointer-events-none'
                  )}
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
                      <span className="font-medium">Deleting…</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="h-3.5 w-3.5 shrink-0" />
                      <span>Delete</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
