'use client';

import { createElement } from 'react';
import type { FileInfo } from '@/types';
import { getFileIcon } from '@/lib/utils/file-utils';
import { Download, Trash2, Copy, X } from 'lucide-react';
import { useFileDownload, useFileDelete } from '@/hooks/use-files';
import { toast } from 'sonner';

interface PreviewModalHeaderProps {
  file: FileInfo;
  sessionId: string;
  content: string | Blob | null;
  onClose: () => void;
}

export function PreviewModalHeader({ file, sessionId, content, onClose }: PreviewModalHeaderProps) {
  const { downloadFile, isDownloading } = useFileDownload(sessionId);
  const { deleteFile } = useFileDelete(sessionId);
  const FileIcon = getFileIcon(file.content_type, file.original_name);

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b">
      <div className="h-8 w-8 rounded-md bg-muted flex items-center justify-center">
        {createElement(FileIcon, { className: 'h-5 w-5' })}
      </div>
      <div className="min-w-0 flex-1">
        <h2 className="text-sm font-semibold truncate">{file.original_name}</h2>
        <p className="text-xs text-muted-foreground">{file.file_type} file</p>
      </div>
      <div className="flex items-center gap-1.5 mr-8">
        <button
          onClick={() => downloadFile(file.file_type, file.safe_name, file.original_name)}
          disabled={isDownloading}
          className="h-8 px-3 rounded-md bg-muted hover:bg-accent text-xs flex items-center"
        >
          <Download className="h-3.5 w-3.5 mr-1.5" />
          Download
        </button>
        {typeof content === 'string' && (
          <button
            onClick={() => {
              navigator.clipboard.writeText(content);
              toast.success('Content copied to clipboard');
            }}
            className="h-8 w-8 rounded-md hover:bg-accent flex items-center justify-center"
            title="Copy to clipboard"
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
        )}
        <button
          onClick={() => {
            deleteFile({ safeName: file.safe_name, fileType: file.file_type });
            onClose();
          }}
          className="h-8 w-8 rounded-md text-destructive hover:bg-destructive/10 flex items-center justify-center"
          title="Delete file"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
      <button
        onClick={onClose}
        className="h-8 w-8 rounded-md hover:bg-accent flex items-center justify-center"
        title="Close"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
