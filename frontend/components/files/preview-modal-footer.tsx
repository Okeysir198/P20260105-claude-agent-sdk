'use client';

import type { FileInfo } from '@/types';
import { formatFileSize } from '@/lib/utils/file-utils';
import { relativeTime } from '@/lib/utils';

export function PreviewModalFooter({ file, content }: { file: FileInfo; content: string | Blob | null }) {
  const lineCount = typeof content === 'string' ? content.split('\n').length : null;
  const charCount = typeof content === 'string' ? content.length : null;

  return (
    <div className="px-3 py-1.5 border-t bg-muted/40 backdrop-blur text-[10px] sm:text-xs">
      {/* Desktop: horizontal layout */}
      <div className="hidden sm:flex items-center justify-center gap-4 flex-wrap">
        <span className="flex items-center gap-1">
          <span className="text-muted-foreground/70 font-medium">Type:</span>
          <span className="tabular-nums">{file.content_type}</span>
        </span>
        <span className="w-px h-3 bg-border/50" />
        <span className="flex items-center gap-1">
          <span className="text-muted-foreground/70 font-medium">Size:</span>
          <span className="tabular-nums">{formatFileSize(file.size_bytes)}</span>
        </span>
        <span className="w-px h-3 bg-border/50" />
        <span className="flex items-center gap-1">
          <span className="text-muted-foreground/70 font-medium">Created:</span>
          <span>{relativeTime(file.created_at)}</span>
        </span>
        {lineCount !== null && (
          <>
            <span className="w-px h-3 bg-border/50" />
            <span className="flex items-center gap-1">
              <span className="text-muted-foreground/70 font-medium">Lines:</span>
              <span className="tabular-nums">{lineCount.toLocaleString()}</span>
            </span>
          </>
        )}
        {charCount !== null && (
          <>
            <span className="w-px h-3 bg-border/50" />
            <span className="flex items-center gap-1">
              <span className="text-muted-foreground/70 font-medium">Chars:</span>
              <span className="tabular-nums">{charCount.toLocaleString()}</span>
            </span>
          </>
        )}
      </div>

      {/* Mobile: compact grid */}
      <div className="sm:hidden grid grid-cols-3 gap-x-4 gap-y-1">
        <span className="text-muted-foreground/70">Type</span>
        <span className="text-muted-foreground/70">Size</span>
        <span className="text-muted-foreground/70">Created</span>
        <span className="tabular-nums truncate">{file.content_type}</span>
        <span className="tabular-nums">{formatFileSize(file.size_bytes)}</span>
        <span>{relativeTime(file.created_at)}</span>
        {lineCount !== null && (
          <>
            <span className="text-muted-foreground/70">Lines</span>
            <span className="text-muted-foreground/70">Chars</span>
            <span></span>
            <span className="tabular-nums">{lineCount.toLocaleString()}</span>
            <span className="tabular-nums">{charCount?.toLocaleString()}</span>
          </>
        )}
      </div>
    </div>
  );
}
