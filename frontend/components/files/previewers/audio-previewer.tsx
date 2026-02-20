'use client';

import { Play, Pause, Volume2, VolumeX, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import type { PreviewerProps } from './index';
import { useMediaPlayer } from './use-media-player';

export function AudioPreviewer({ file, content }: PreviewerProps) {
  const {
    isPlaying, currentTime, duration, volume, isMuted,
    mediaUrl, mediaRef, togglePlayPause, handleTimeUpdate,
    handleLoadedMetadata, handleSeek, handleVolumeChange,
    toggleMute, handleEnded, handlePlay, handlePause,
    handleDownload, formatTime,
  } = useMediaPlayer(content, file.original_name);

  return (
    <div className="flex items-center justify-center h-full p-4 sm:p-8">
      <div className="w-full max-w-2xl">
        {mediaUrl && (
          <audio
            ref={mediaRef as React.RefObject<HTMLAudioElement>}
            src={mediaUrl}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={handleEnded}
            onPlay={handlePlay}
            onPause={handlePause}
          />
        )}

        {/* File info */}
        <div className="text-center mb-6">
          <h3 className="text-lg font-semibold mb-1 truncate px-4">{file.original_name}</h3>
          <p className="text-sm text-muted-foreground">
            {file.content_type} • {(file.size_bytes / 1024).toFixed(1)} KB
          </p>
        </div>

        {/* Audio player controls */}
        <div className="bg-muted/30 rounded-xl p-4 sm:p-6 space-y-4">
          {/* Progress bar */}
          <div className="space-y-2">
            <Slider
              value={[currentTime]}
              max={duration || 100}
              step={0.1}
              onValueChange={handleSeek}
              className="cursor-pointer"
            />
            <div className="flex justify-between text-xs text-muted-foreground px-1">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-center gap-4">
            <Button
              onClick={togglePlayPause}
              size="lg"
              className="h-14 w-14 rounded-full"
            >
              {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6 ml-1" />}
            </Button>

            {/* Volume control */}
            <div className="flex items-center gap-2">
              <Button onClick={toggleMute} variant="ghost" size="icon" className="h-9 w-9">
                {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </Button>
              <div className="w-20">
                <Slider
                  value={[isMuted ? 0 : volume]}
                  max={1}
                  step={0.01}
                  onValueChange={handleVolumeChange}
                  className="cursor-pointer"
                />
              </div>
            </div>

            <Button onClick={handleDownload} variant="outline" size="icon" className="h-9 w-9" title="Download audio file">
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AudioPreviewer;
