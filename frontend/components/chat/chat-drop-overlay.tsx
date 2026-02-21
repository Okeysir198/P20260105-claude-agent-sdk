'use client';

import { Upload } from 'lucide-react';

interface ChatDropOverlayProps {
  isDragActive: boolean;
}

export function ChatDropOverlay({ isDragActive }: ChatDropOverlayProps) {
  if (!isDragActive) return null;

  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center rounded-2xl border-2 border-dashed border-primary/50 bg-primary/5 backdrop-blur-[2px]">
      <div className="flex flex-col items-center gap-2 text-primary/70">
        <Upload className="h-6 w-6" />
        <span className="text-sm font-medium">Drop files to attach</span>
      </div>
    </div>
  );
}
