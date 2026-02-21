'use client';

import { useState } from 'react';

interface InlineImageProps {
  src: string;
  alt?: string;
  onClickZoom?: (src: string) => void;
}

export function InlineImage({ src, alt, onClickZoom }: InlineImageProps) {
  const [loaded, setLoaded] = useState(false);

  return (
    <div className="relative w-full sm:w-auto sm:max-w-[280px]">
      {/* Loading skeleton */}
      {!loaded && (
        <div className="w-full sm:w-[280px] h-[180px] rounded-lg bg-muted/60 animate-pulse border border-border/20" />
      )}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt || 'Image'}
        className={`max-w-full rounded-lg border border-border/20 object-contain ${
          onClickZoom ? 'cursor-pointer' : ''
        } ${loaded ? '' : 'hidden'}`}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        onClick={() => onClickZoom?.(src)}
      />
    </div>
  );
}
