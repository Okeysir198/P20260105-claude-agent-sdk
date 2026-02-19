'use client';

import { useRef, useState } from 'react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { ZoomIn, ZoomOut, RotateCw, Undo2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { PreviewerProps } from './index';

export function ImagePreviewer({ file, content }: PreviewerProps) {
  const [rotation, setRotation] = useState(0);
  const imageUrl = useRef(URL.createObjectURL(content as Blob));

  return (
    <div className="relative flex flex-col h-full bg-muted/20">
      <TransformWrapper
        initialScale={1}
        initialPositionX={0}
        initialPositionY={0}
      >
        {({ zoomIn, zoomOut, resetTransform }) => (
          <>
            {/* Floating toolbar - modern and compact */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 px-1.5 py-1.5 bg-background/90 backdrop-blur-md rounded-full shadow-lg border border-border/50">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => zoomIn()}
                className="h-8 w-8 rounded-full"
                title="Zoom in"
              >
                <ZoomIn className="h-4 w-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => zoomOut()}
                className="h-8 w-8 rounded-full"
                title="Zoom out"
              >
                <ZoomOut className="h-4 w-4" />
              </Button>

              <div className="w-px h-5 bg-border/50 mx-1" />

              <Button
                variant="ghost"
                size="icon"
                onClick={() => setRotation((p) => (p - 90) % 360)}
                className="h-8 w-8 rounded-full"
                title="Rotate left"
              >
                <Undo2 className="h-4 w-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => setRotation((p) => (p + 90) % 360)}
                className="h-8 w-8 rounded-full"
                title="Rotate right"
              >
                <RotateCw className="h-4 w-4" />
              </Button>

              <div className="w-px h-5 bg-border/50 mx-1" />

              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  resetTransform();
                  setRotation(0);
                }}
                className="h-7 px-3 rounded-full text-xs font-medium"
                title="Reset view"
              >
                Reset
              </Button>
            </div>

            <div className="flex-1 overflow-hidden flex items-center justify-center bg-checkered">
              <TransformComponent
                wrapperStyle={{ width: '100%', height: '100%' }}
                contentStyle={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <img
                  src={imageUrl.current}
                  alt={file.original_name}
                  className="max-w-full max-h-full object-contain rounded shadow-2xl"
                  style={{
                    transform: `rotate(${rotation}deg)`,
                    transition: 'transform 0.3s ease-out',
                    imageRendering: 'auto'
                  }}
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
