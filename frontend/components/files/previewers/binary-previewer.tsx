'use client';

import { Download, FileQuestion } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { PreviewerProps } from './index';

export function BinaryPreviewer({ file, content }: PreviewerProps) {
  const handleDownload = () => {
    const url = URL.createObjectURL(content as Blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = file.original_name;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center justify-center h-full p-4 sm:p-8">
      <div className="text-center max-w-sm">
        <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-muted/60 flex items-center justify-center mx-auto mb-3 sm:mb-4">
          <FileQuestion className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
        </div>
        <h3 className="text-base sm:text-lg font-semibold mb-1 sm:mb-2">Preview not available</h3>
        <p className="text-xs sm:text-sm text-muted-foreground mb-4 sm:mb-6 px-4">
          {file.content_type} • {(file.size_bytes / 1024).toFixed(1)} KB
        </p>
        <Button
          onClick={handleDownload}
          size="sm"
          className="h-8 sm:h-9 px-4 gap-2"
        >
          <Download className="h-4 w-4" />
          Download to view
        </Button>
      </div>
    </div>
  );
}

export default BinaryPreviewer;
