'use client';

import { useEffect, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { useLightboxStore } from '@/lib/store/lightbox-store';

export function ImageLightbox() {
  const { isOpen, images, currentIndex, close, next, prev } = useLightboxStore();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;
      switch (e.key) {
        case 'Escape':
          close();
          break;
        case 'ArrowLeft':
          prev();
          break;
        case 'ArrowRight':
          next();
          break;
      }
    },
    [isOpen, close, next, prev],
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Prevent body scroll when lightbox is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen || images.length === 0) return null;

  const currentSrc = images[currentIndex];
  const hasMultiple = images.length > 1;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
      onClick={close}
      role="dialog"
      aria-modal="true"
      aria-label="Image viewer"
    >
      {/* Close button */}
      <button
        type="button"
        onClick={close}
        className="absolute top-4 right-4 z-10 flex items-center justify-center w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
        aria-label="Close"
      >
        <X className="h-5 w-5 text-white" />
      </button>

      {/* Image counter */}
      {hasMultiple && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 px-3 py-1.5 rounded-full bg-black/50 text-white text-sm font-mono tabular-nums">
          {currentIndex + 1} / {images.length}
        </div>
      )}

      {/* Previous button */}
      {hasMultiple && currentIndex > 0 && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            prev();
          }}
          className="absolute left-4 z-10 flex items-center justify-center w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
          aria-label="Previous image"
        >
          <ChevronLeft className="h-6 w-6 text-white" />
        </button>
      )}

      {/* Next button */}
      {hasMultiple && currentIndex < images.length - 1 && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            next();
          }}
          className="absolute right-4 z-10 flex items-center justify-center w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
          aria-label="Next image"
        >
          <ChevronRight className="h-6 w-6 text-white" />
        </button>
      )}

      {/* Image with zoom/pan */}
      <div
        className="w-full h-full flex items-center justify-center p-8 sm:p-16"
        onClick={(e) => e.stopPropagation()}
      >
        <TransformWrapper
          key={currentIndex}
          initialScale={1}
          minScale={0.5}
          maxScale={5}
          centerOnInit
          wheel={{ step: 0.1 }}
          doubleClick={{ mode: 'reset' }}
        >
          <TransformComponent
            wrapperStyle={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            contentStyle={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={currentSrc}
              alt={`Image ${currentIndex + 1}`}
              className="max-w-full max-h-[80vh] object-contain select-none"
              draggable={false}
            />
          </TransformComponent>
        </TransformWrapper>
      </div>
    </div>
  );
}
