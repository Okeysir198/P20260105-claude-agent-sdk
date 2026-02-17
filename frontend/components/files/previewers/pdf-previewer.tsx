'use client';

import { useRef, useEffect } from 'react';
import type { PreviewerProps } from './index';

export function PdfPreviewer({ content }: PreviewerProps) {
  const objectUrl = useRef(URL.createObjectURL(content as Blob));

  useEffect(() => () => URL.revokeObjectURL(objectUrl.current), []);

  return (
    <div className="h-full w-full">
      <iframe src={objectUrl.current} className="w-full h-full border-0" title="PDF preview" />
    </div>
  );
}

export default PdfPreviewer;
