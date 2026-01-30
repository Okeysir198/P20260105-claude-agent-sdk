'use client';

import { X } from 'lucide-react';
import type { ImageContentBlock } from '@/types';

interface ImageAttachmentProps {
  image: ImageContentBlock;
  index: number;
  onRemove: (index: number) => void;
  disabled?: boolean;
}

export function ImageAttachment({ image, index, onRemove, disabled }: ImageAttachmentProps) {
  const src = image.source.type === 'url'
    ? image.source.url
    : `data:image;base64,${image.source.data}`;

  return (
    <div className="relative h-20 w-20 rounded-lg border border-border overflow-hidden shrink-0">
      <img
        src={src}
        alt={`Attachment ${index + 1}`}
        className="h-full w-full object-cover"
      />
      <button
        type="button"
        onClick={() => onRemove(index)}
        className="absolute top-1 right-1 h-5 w-5 rounded-full bg-destructive text-white hover:bg-destructive/90 flex items-center justify-center"
        disabled={disabled}
        title="Remove image"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}
