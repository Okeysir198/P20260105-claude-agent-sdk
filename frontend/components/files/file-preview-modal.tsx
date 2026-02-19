'use client';

import { useState, useCallback, useRef, useEffect, Suspense, lazy } from 'react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Loader2 } from 'lucide-react';
import { useFilePreviewStore } from '@/lib/store/file-preview-store';
import { useFileContent } from '@/hooks/use-files';
import { getPreviewType } from '@/lib/utils/file-utils';
import { PreviewModalHeader } from './preview-modal-header';
import { PreviewModalFooter } from './preview-modal-footer';

// Lazy load previewers for performance
const ImagePreviewer = lazy(() => import('./previewers/image-previewer'));
const CodePreviewer = lazy(() => import('./previewers/code-previewer'));
const JsonPreviewer = lazy(() => import('./previewers/json-previewer'));
const TextPreviewer = lazy(() => import('./previewers/text-previewer'));
const PdfPreviewer = lazy(() => import('./previewers/pdf-previewer'));
const BinaryPreviewer = lazy(() => import('./previewers/binary-previewer'));
const ExcelPreviewer = lazy(() => import('./previewers/excel-previewer'));

const PREVIEWER_COMPONENTS = {
  image: ImagePreviewer,
  code: CodePreviewer,
  json: JsonPreviewer,
  text: TextPreviewer,
  pdf: PdfPreviewer,
  markdown: CodePreviewer,
  binary: BinaryPreviewer,
  spreadsheet: ExcelPreviewer,
} as const;

export function FilePreviewModal() {
  const { isOpen, file, sessionId, closePreview } = useFilePreviewStore();
  const [modalWidth, setModalWidth] = useState(1000);
  const { data: content, isLoading, error } = useFileContent(sessionId || '', file);

  useEffect(() => {
    if (isOpen) {
      const vw = window.innerWidth;
      // Mobile: nearly fullscreen, Desktop: 85% width
      setModalWidth(vw < 640 ? vw - 16 : Math.min(1400, vw * 0.85));
    }
  }, [isOpen]);

  const resizeRef = useRef({ startX: 0, startWidth: 0 });

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    resizeRef.current = { startX: e.clientX, startWidth: modalWidth };
    document.body.style.cursor = 'ew-resize';

    const onMove = (ev: MouseEvent) => {
      const delta = ev.clientX - resizeRef.current.startX;
      const newWidth = Math.max(360, Math.min(window.innerWidth * 0.95, resizeRef.current.startWidth + delta * 2));
      setModalWidth(newWidth);
    };

    const onUp = () => {
      document.body.style.cursor = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [modalWidth]);

  if (!file) return null;

  const PreviewerComponent = PREVIEWER_COMPONENTS[getPreviewType(file)];
  const previewType = getPreviewType(file);
  const usesOwnScroll = previewType === 'pdf' || previewType === 'spreadsheet';

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closePreview()}>
      <DialogContent
        className="sm:max-w-none !p-0 overflow-hidden flex flex-col [&>button:last-child]:hidden max-h-[95dvh]"
        style={{
          width: modalWidth,
          height: '85dvh',
        }}
      >
        {/* Visually hidden title for screen readers */}
        <DialogTitle className="sr-only">Preview: {file.original_name}</DialogTitle>

        {/* Resize handle - desktop only */}
        <div className="hidden md:block absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize z-10" onMouseDown={handleResizeStart}>
          <div className="absolute right-0 top-1/2 -translate-y-1/2 h-10 w-1 rounded-full bg-border hover:bg-primary/50 transition-colors" />
        </div>

        <PreviewModalHeader file={file} sessionId={sessionId!} content={content ?? null} onClose={closePreview} />

        {/* PDF and spreadsheet manage their own scrolling */}
        <div className={usesOwnScroll ? "flex-1 overflow-hidden min-h-0 relative" : "flex-1 overflow-y-auto min-h-0"}>
          {isLoading ? (
            <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
          ) : error ? (
            <div className="p-4 text-destructive text-sm">Failed to load file</div>
          ) : content ? (
            <Suspense fallback={<div className="flex items-center justify-center h-full"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>}>
              <PreviewerComponent file={file} content={content} />
            </Suspense>
          ) : null}
        </div>

        <PreviewModalFooter file={file} content={content ?? null} />
      </DialogContent>
    </Dialog>
  );
}
