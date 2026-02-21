'use client';

import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize, Download, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import type { PreviewerProps } from './index';
import { useMediaPlayer } from './use-media-player';

export function VideoPreviewer({ file, content }: PreviewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const {
    isPlaying, currentTime, duration, volume, isMuted, error,
    mediaUrl, mediaRef, togglePlayPause, handleTimeUpdate,
    handleLoadedMetadata, handleSeek, handleVolumeChange,
    toggleMute, handleEnded, handlePlay, handlePause,
    handleError, handleDownload, formatTime,
  } = useMediaPlayer(content, file.original_name);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (isFullscreen) {
      document.exitFullscreen();
    } else {
      containerRef.current.requestFullscreen();
    }
  };

  useEffect(() => {
    function handleFullscreenChange() {
      setIsFullscreen(!!document.fullscreenElement);
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  return (
    <div ref={containerRef} className="flex items-center justify-center h-full p-4 sm:p-8">
      <div className="w-full max-w-4xl">
        {mediaUrl && (
          <video
            ref={mediaRef as React.RefObject<HTMLVideoElement>}
            src={mediaUrl}
            className="w-full rounded-lg bg-black"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={handleEnded}
            onPlay={handlePlay}
            onPause={handlePause}
            onError={handleError}
            controls={false}
          />
        )}

        {/* Error message */}
        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-lg p-3 mt-3">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Controls */}
        <div className="bg-muted/30 rounded-lg p-3 sm:p-4 mt-3 space-y-3">
          {/* Progress bar */}
          <div className="space-y-1">
            <Slider
              value={[currentTime]}
              max={duration || 100}
              step={0.1}
              onValueChange={handleSeek}
              className="cursor-pointer"
            />
            <div className="flex justify-between text-xs text-muted-foreground px-1">
              <span>{formatTime(currentTime)}</span>
              <span className="text-xs">{file.original_name}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* Control buttons */}
          <div className="flex items-center justify-center gap-3">
            <Button onClick={togglePlayPause} size="icon" variant="default" className="h-10 w-10" disabled={!!error}>
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
            </Button>

            {/* Volume */}
            <div className="flex items-center gap-2">
              <Button onClick={toggleMute} variant="ghost" size="icon" className="h-9 w-9">
                {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </Button>
              <div className="w-20 hidden sm:block">
                <Slider
                  value={[isMuted ? 0 : volume]}
                  max={1}
                  step={0.01}
                  onValueChange={handleVolumeChange}
                  className="cursor-pointer"
                />
              </div>
            </div>

            <Button onClick={toggleFullscreen} variant="ghost" size="icon" className="h-9 w-9" title="Toggle fullscreen">
              <Maximize className="h-4 w-4" />
            </Button>

            <Button onClick={handleDownload} variant="outline" size="icon" className="h-9 w-9" title="Download video file">
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* File info */}
        <div className="text-center mt-3">
          <p className="text-xs text-muted-foreground">
            {file.content_type} • {(file.size_bytes / 1024).toFixed(1)} KB
          </p>
        </div>
      </div>
    </div>
  );
}

export default VideoPreviewer;
