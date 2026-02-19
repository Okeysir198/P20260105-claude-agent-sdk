'use client';

import { createElement, useState } from 'react';
import type { FileInfo } from '@/types';
import { getFileIcon } from '@/lib/utils/file-utils';
import { Download, Trash2, Copy, X, MoreVertical } from 'lucide-react';
import { useFileDownload, useFileDelete } from '@/hooks/use-files';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

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
  const [showMore, setShowMore] = useState(false);

  const handleCopy = () => {
    if (typeof content === 'string') {
      navigator.clipboard.writeText(content);
      toast.success('Copied to clipboard');
    }
  };

  const handleDelete = () => {
    deleteFile({ safeName: file.safe_name, fileType: file.file_type });
    onClose();
  };

  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      {/* File icon - compact */}
      <div className="h-7 w-7 rounded bg-muted/60 flex items-center justify-center flex-shrink-0">
        {createElement(FileIcon, { className: 'h-4 w-4 text-muted-foreground' })}
      </div>

      {/* File info */}
      <div className="min-w-0 flex-1">
        <h2 className="text-sm font-medium truncate text-foreground">{file.original_name}</h2>
      </div>

      {/* Action buttons - desktop */}
      <div className="hidden sm:flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => downloadFile(file.file_type, file.safe_name, file.original_name)}
          disabled={isDownloading}
          className="h-7 px-2 text-xs gap-1.5"
        >
          <Download className="h-3.5 w-3.5" />
          <span className="hidden xs:inline">Download</span>
        </Button>

        {typeof content === 'string' && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCopy}
            className="h-7 w-7"
            title="Copy to clipboard"
          >
            <Copy className="h-3.5 w-3.5" />
          </Button>
        )}

        <Button
          variant="ghost"
          size="icon"
          onClick={handleDelete}
          className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
          title="Delete file"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-7 w-7"
          title="Close"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Mobile: more menu + close */}
      <div className="flex sm:hidden items-center gap-1">
        <DropdownMenu open={showMore} onOpenChange={setShowMore}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              title="More actions"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={() => downloadFile(file.file_type, file.safe_name, file.original_name)}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </DropdownMenuItem>
            {typeof content === 'string' && (
              <DropdownMenuItem onClick={handleCopy}>
                <Copy className="h-4 w-4 mr-2" />
                Copy content
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={handleDelete} className="text-destructive focus:text-destructive">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete file
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-7 w-7"
          title="Close"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
