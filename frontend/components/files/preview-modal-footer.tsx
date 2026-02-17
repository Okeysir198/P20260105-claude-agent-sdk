'use client';

import type { FileInfo } from '@/types';
import { formatFileSize } from '@/lib/utils/file-utils';
import { relativeTime } from '@/lib/utils';

export function PreviewModalFooter({ file, content }: { file: FileInfo; content: string | Blob | null }) {
  return (
    <div className="flex items-center gap-4 px-6 py-3 border-t bg-muted/30 text-xs">
      <div>
        <span className="font-medium text-muted-foreground uppercase">Type</span> {file.content_type}
      </div>
      <div>
        <span className="font-medium text-muted-foreground uppercase">Size</span> {formatFileSize(file.size_bytes)}
      </div>
      <div>
        <span className="font-medium text-muted-foreground uppercase">Created</span> {relativeTime(file.created_at)}
      </div>
      {typeof content === 'string' && (
        <>
          <div>
            <span className="font-medium text-muted-foreground uppercase">Lines</span> {content.split('\n').length.toLocaleString()}
          </div>
          <div>
            <span className="font-medium text-muted-foreground uppercase">Characters</span> {content.length.toLocaleString()}
          </div>
        </>
      )}
    </div>
  );
}
