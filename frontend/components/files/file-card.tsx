'use client';

import { createElement } from 'react';
import { cn, relativeTime } from '@/lib/utils';
import { getFileIcon as getFileIconUtil, formatFileSize } from '@/lib/utils/file-utils';
import { Download, Trash2 } from 'lucide-react';
import type { FileMetadata } from '@/types';

interface FileCardProps {
  file: FileMetadata;
  onDownload: (file: FileMetadata) => void;
  onDelete: (safeName: string) => void;
}

export function FileCard({ file, onDownload, onDelete }: FileCardProps) {
  const FileIcon = getFileIconUtil(file.content_type, file.original_name);
  const isInput = file.file_type === 'input';

  return (
    <div
      className={cn(
        'group relative flex items-center gap-3',
        'bg-card border rounded-lg p-3 shadow-sm',
        'hover:shadow-md hover:border-primary/50',
        'transition-all duration-150',
        'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-1'
      )}
    >
      {/* File Icon */}
      <div className="flex shrink-0 items-center justify-center">
        {createElement(FileIcon, {
          className: 'h-5 w-5 text-muted-foreground',
          'aria-hidden': 'true',
        })}
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
          <span className="text-xs text-muted-foreground">
            {formatFileSize(file.size_bytes)}
          </span>
          <span className="text-xs text-muted-foreground/50">•</span>
          <span className="text-xs text-muted-foreground">
            {relativeTime(file.created_at)}
          </span>
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
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          onClick={() => onDownload(file)}
          className={cn(
            'inline-flex items-center justify-center',
            'h-7 w-7 rounded-md',
            'hover:bg-accent hover:text-accent-foreground',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
            'transition-colors',
            'text-muted-foreground'
          )}
          title="Download file"
          aria-label={`Download ${file.original_name}`}
        >
          <Download className="h-3.5 w-3.5" />
        </button>

        <button
          type="button"
          onClick={() => onDelete(file.safe_name)}
          className={cn(
            'inline-flex items-center justify-center',
            'h-7 w-7 rounded-md',
            'hover:bg-destructive/10 hover:text-destructive',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
            'transition-colors',
            'text-muted-foreground'
          )}
          title="Delete file"
          aria-label={`Delete ${file.original_name}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
