'use client';

interface InlineVideoPlayerProps {
  src: string;
  filename?: string;
  mimeType?: string;
}

export function InlineVideoPlayer({ src, filename, mimeType }: InlineVideoPlayerProps) {
  return (
    <div className="w-full sm:w-auto sm:max-w-[320px]">
      <video
        src={src}
        controls
        preload="metadata"
        className="w-full rounded-lg border border-border/20 aspect-video object-contain bg-black"
        aria-label={filename || 'Video'}
      >
        {mimeType && <source src={src} type={mimeType} />}
        Your browser does not support the video element.
      </video>
    </div>
  );
}
