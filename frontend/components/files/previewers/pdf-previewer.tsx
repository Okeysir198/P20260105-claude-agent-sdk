'use client';

import { useRef, useEffect } from 'react';
import type { PreviewerProps } from './index';

export function PdfPreviewer({ content }: PreviewerProps) {
  const objectUrl = useRef(URL.createObjectURL(content as Blob));

  useEffect(() => () => URL.revokeObjectURL(objectUrl.current), []);

  return (
    <iframe
      src={objectUrl.current}
      className="absolute inset-0 w-full h-full border-0"
      title="PDF preview"
    />
  );
}

export default PdfPreviewer;
