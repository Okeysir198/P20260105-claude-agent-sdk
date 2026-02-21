'use client';

import { Download } from 'lucide-react';
import { getFileIcon, getFileColorClasses, formatFileSize } from '@/lib/utils/file-utils';
import { createElement } from 'react';

interface InlineFileCardProps {
  filename: string;
  url: string;
  size?: number;
  mimeType?: string;
}

export function InlineFileCard({ filename, url, size, mimeType }: InlineFileCardProps) {
  const colors = getFileColorClasses(mimeType, filename);
  const icon = createElement(getFileIcon(mimeType, filename), {
    className: `h-4 w-4 ${colors.iconColor}`,
  });

  return (
    <div className="w-full sm:w-auto sm:max-w-[280px] flex items-center gap-3 px-3 py-2.5 rounded-lg bg-muted/40 border border-border/20">
      {/* File type icon */}
      <div className={`flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-md ${colors.bgColor}`}>
        {icon}
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-foreground truncate" title={filename}>
          {filename}
        </p>
        {size != null && size > 0 && (
          <p className="text-[11px] text-muted-foreground">{formatFileSize(size)}</p>
        )}
      </div>

      {/* Download button */}
      <a
        href={url}
        download={filename}
        className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-md hover:bg-foreground/10 transition-colors"
        aria-label={`Download ${filename}`}
      >
        <Download className="h-4 w-4 text-muted-foreground" />
      </a>
    </div>
  );
}
