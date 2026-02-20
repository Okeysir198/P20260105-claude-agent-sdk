'use client';

import { useEffect, useRef, useState } from 'react';
import { Table, FileSpreadsheet, AlertCircle } from 'lucide-react';
import type { PreviewerProps } from './index';
import '@js-preview/excel/lib/index.css';

export function ExcelPreviewer({ file, content }: PreviewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let previewerInstance: any = null;

    const initPreviewer = async () => {
      if (!containerRef.current || !(content instanceof Blob)) {
        setError('Invalid content for Excel preview');
        setLoading(false);
        return;
      }

      try {
        // Check if this might be a PDF (gsheet files are PDFs)
        const buffer = await content.arrayBuffer();
        const arr = new Uint8Array(buffer.slice(0, 4));
        const header = String.fromCharCode(...arr);

        if (header === '%PDF') {
          setError(
            'This file is a PDF export from Google Sheets. To view as a spreadsheet:\n' +
            '1. Open the file in Google Sheets\n' +
            '2. File → Download → Microsoft Excel (.xlsx)\n' +
            '3. Upload the .xlsx file'
          );
          setLoading(false);
          return;
        }

        // Dynamically import @js-preview/excel
        const { excelPreviewer } = await import('@js-preview/excel');

        // Create a new blob from the buffer for the previewer
        const excelBlob = new Blob([buffer], { type: content.type || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

        // Initialize the previewer
        previewerInstance = excelPreviewer(containerRef.current, excelBlob);

        setLoading(false);
      } catch (err) {
        console.error('[ExcelPreviewer] Init error:', err);
        setError(err instanceof Error ? err.message : 'Failed to initialize Excel viewer');
        setLoading(false);
      }
    };

    initPreviewer();

    // Cleanup on unmount
    return () => {
      if (previewerInstance && typeof previewerInstance.destroy === 'function') {
        previewerInstance.destroy();
      }
    };
  }, [content]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <div className="h-8 w-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading spreadsheet…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <div className="text-center max-w-lg">
          <div className="flex items-center justify-center gap-2 mb-3 text-destructive">
            <AlertCircle className="h-5 w-5" />
            <span className="font-medium">Cannot preview as spreadsheet</span>
          </div>
          <p className="text-sm text-muted-foreground whitespace-pre-line">{error}</p>
          {error.includes('PDF') && (
            <div className="mt-4 p-3 bg-amber-500/10 dark:bg-amber-500/20 border border-amber-500/30 rounded-lg text-left">
              <div className="flex items-start gap-2">
                <FileSpreadsheet className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                <div className="text-xs">
                  <p className="font-medium text-amber-700 dark:text-amber-300 mb-1">Tip for Google Sheets</p>
                  <p className="text-amber-600/80 dark:text-amber-400/80">
                    When downloading from Google Sheets, use <strong>File → Download → Microsoft Excel (.xlsx)</strong> to get the actual spreadsheet file.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full overflow-auto">
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
}

export default ExcelPreviewer;
