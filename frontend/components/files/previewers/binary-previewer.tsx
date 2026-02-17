'use client';

import { Download, FileQuestion } from 'lucide-react';
import type { PreviewerProps } from './index';

export function BinaryPreviewer({ file, content }: PreviewerProps) {
  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="text-center">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
          <FileQuestion className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold mb-2">Preview not available</h3>
        <p className="text-sm text-muted-foreground mb-4">{file.content_type} • {file.size_bytes} bytes</p>
        <button onClick={() => { const url = URL.createObjectURL(content as Blob); const a = document.createElement('a'); a.href = url; a.download = file.original_name; a.click(); }} className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 text-sm">
          <Download className="h-4 w-4" />Download to view
        </button>
      </div>
    </div>
  );
}

export default BinaryPreviewer;
