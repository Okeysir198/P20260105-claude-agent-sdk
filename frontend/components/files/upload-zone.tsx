'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FilePlus, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatFileSize } from '@/lib/utils/file-utils';

interface UploadZoneProps {
  onUpload: (files: File[]) => void;
  isUploading?: boolean;
  uploadProgress?: Map<string, number>; // filename -> progress (0-100)
}

export function UploadZone({ onUpload, isUploading = false, uploadProgress = new Map() }: UploadZoneProps) {
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

  const hasProgress = uploadProgress.size > 0;
  const isExpanded = isDragActive || hasProgress;

  return (
    <div
      {...getRootProps()}
      className={cn(
        'relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-4 transition-all duration-200 cursor-pointer',
        'hover:border-primary hover:bg-primary/5',
        isDragging
          ? 'border-primary bg-primary/10 h-40'
          : 'border-border h-20',
        isUploading && 'opacity-60 cursor-not-allowed'
      )}
    >
      <input {...getInputProps()} disabled={isUploading} />

      {/* Main Icon */}
      <div className="mb-2">
        {isDragActive ? (
          <FilePlus className="h-8 w-8 text-primary" />
        ) : (
          <UploadCloud className={cn('h-6 w-6', hasProgress ? 'text-primary' : 'text-muted-foreground')} />
        )}
      </div>

      {/* Text Content */}
      {isDragActive ? (
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">Drop files to upload</p>
          <p className="text-xs text-muted-foreground mt-1">
            Supported: PDF, DOC, XLS, Images, Code, Archives
          </p>
        </div>
      ) : hasProgress ? (
        <div className="w-full max-w-xs space-y-2">
          {Array.from(uploadProgress.entries()).map(([filename, progress]) => (
            <div key={filename} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="truncate max-w-[150px]" title={filename}>
                  {filename}
                </span>
                <span className="text-muted-foreground">{progress}%</span>
              </div>
              <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-center text-muted-foreground">
          Drop files here or click to browse
        </p>
      )}

      {/* Close button for cancelling uploads */}
      {hasProgress && !isUploading && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onUpload([]);
          }}
          className="absolute top-2 right-2 p-1 rounded-md hover:bg-accent"
          aria-label="Cancel uploads"
        >
          <X className="h-4 w-4 text-muted-foreground" />
        </button>
      )}
    </div>
  );
}
