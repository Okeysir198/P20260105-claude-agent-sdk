'use client';

import { useRef, useState } from 'react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import type { PreviewerProps } from './index';

export function ImagePreviewer({ file, content }: PreviewerProps) {
  const [rotation, setRotation] = useState(0);
  const imageUrl = useRef(URL.createObjectURL(content as Blob));

  return (
    <div className="relative flex flex-col h-full bg-muted/30">
      <TransformWrapper
        initialScale={1}
        initialPositionX={0}
        initialPositionY={0}
      >
        {({ zoomIn, zoomOut, resetTransform }) => (
          <>
            <div className="flex items-center justify-center gap-2 py-2 border-b">
              <button onClick={() => zoomIn()} className="p-2 rounded-md hover:bg-accent"><ZoomIn className="h-4 w-4" /></button>
              <button onClick={() => zoomOut()} className="p-2 rounded-md hover:bg-accent"><ZoomOut className="h-4 w-4" /></button>
              <button onClick={() => resetTransform()} className="px-3 py-1.5 text-xs rounded-md hover:bg-accent">Reset</button>
              <button onClick={() => setRotation((p) => (p + 90) % 360)} className="p-2 rounded-md hover:bg-accent"><RotateCw className="h-4 w-4" /></button>
            </div>
            <div className="flex-1 overflow-hidden flex items-center justify-center p-4">
              <TransformComponent
                wrapperStyle={{ width: '100%', height: '100%' }}
                contentStyle={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <img
                  src={imageUrl.current}
                  alt={file.original_name}
                  className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                  style={{ transform: `rotate(${rotation}deg)`, transition: 'transform 0.3s' }}
                />
              </TransformComponent>
            </div>
          </>
        )}
      </TransformWrapper>
    </div>
  );
}

export default ImagePreviewer;
