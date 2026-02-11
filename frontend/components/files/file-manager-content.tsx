'use client';

import { useFileOperations } from '@/hooks/use-files';
import { ScrollArea } from '@/components/ui/scroll-area';
import { UploadZone } from './upload-zone';
import { FileCard } from './file-card';
import { Loader2, FolderOpen } from 'lucide-react';
import { useUIStore } from '@/lib/store/ui-store';
import { useChatStore } from '@/lib/store/chat-store';
import type { FileMetadata } from '@/types';
import { formatFileSize } from '@/lib/utils/file-utils';

interface FileManagerContentProps {
  sessionId: string;
}

export function FileManagerContent({ sessionId }: FileManagerContentProps) {
  const activeTab = useUIStore((s) => s.sidebarActiveTab);

  // Only load files when the files tab is active
  const {
    files,
    isLoadingFiles,
    uploadFile,
    isUploading,
    deleteFile,
    isDeleting,
    downloadFile,
  } = useFileOperations(sessionId);

  const handleFileSelect = async (file: File) => {
    try {
      await uploadFile({ file });
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const handleDelete = async (safeName: string, fileType: 'input' | 'output') => {
    try {
      await deleteFile({ safeName, fileType });
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const handleDownload = async (file: FileMetadata) => {
    try {
      await downloadFile(file.file_type, file.safe_name, file.original_name);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  // Calculate total size
  const totalSizeBytes = files.reduce((sum, file) => sum + file.size_bytes, 0);
  const totalSizeFormatted = formatFileSize(totalSizeBytes);

  const handleUpload = async (filesToUpload: File[]) => {
    for (const file of filesToUpload) {
      await handleFileSelect(file);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Upload zone at top */}
      <UploadZone onUpload={handleUpload} isUploading={isUploading} />

      {/* File list */}
      <ScrollArea className="flex-1 mt-2">
        <div className="px-2 pb-2 space-y-1">
          {isLoadingFiles ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : files.length > 0 ? (
            files.map((file) => (
              <FileCard
                key={`${file.file_type}-${file.safe_name}`}
                file={file}
                onDownload={handleDownload}
                onDelete={() => handleDelete(file.safe_name, file.file_type)}
              />
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
                <FolderOpen className="h-6 w-6 text-muted-foreground" />
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
