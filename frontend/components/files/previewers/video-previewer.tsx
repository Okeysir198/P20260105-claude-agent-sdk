'use client';

import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import type { PreviewerProps } from './index';

export function VideoPreviewer({ file, content }: PreviewerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const videoUrl = useRef<string>('');

  useEffect(() => {
    // Create object URL for the video blob
    if (content instanceof Blob) {
      videoUrl.current = URL.createObjectURL(content);
      return () => {
        URL.revokeObjectURL(videoUrl.current);
      };
    }
  }, [content]);

  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (value: number[]) => {
    const newTime = value[0];
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const handleVolumeChange = (value: number[]) => {
    const newVolume = value[0];
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
      setVolume(newVolume);
      setIsMuted(newVolume === 0);
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      if (isMuted) {
        videoRef.current.volume = volume || 1;
        setIsMuted(false);
      } else {
        videoRef.current.volume = 0;
        setIsMuted(true);
      }
    }
  };

  const toggleFullscreen = () => {
    if (containerRef.current) {
      if (!isFullscreen) {
        containerRef.current.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const handleDownload = () => {
    if (content instanceof Blob) {
      const url = URL.createObjectURL(content);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.original_name;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div ref={containerRef} className="flex items-center justify-center h-full p-4 sm:p-8">
      <div className="w-full max-w-4xl">
        {/* Video element */}
        {videoUrl.current && (
          <video
            ref={videoRef}
            src={videoUrl.current}
            className="w-full rounded-lg bg-black"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={() => setIsPlaying(false)}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            controls={false}
          />
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
            {/* Play/Pause */}
            <Button
              onClick={togglePlayPause}
              size="icon"
              variant="default"
              className="h-10 w-10"
            >
              {isPlaying ? (
                <Pause className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4 ml-0.5" />
              )}
            </Button>

            {/* Volume */}
            <div className="flex items-center gap-2">
              <Button
                onClick={toggleMute}
                variant="ghost"
                size="icon"
                className="h-9 w-9"
              >
                {isMuted ? (
                  <VolumeX className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
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

            {/* Fullscreen */}
            <Button
              onClick={toggleFullscreen}
              variant="ghost"
              size="icon"
              className="h-9 w-9"
              title="Toggle fullscreen"
            >
              <Maximize className="h-4 w-4" />
            </Button>

            {/* Download */}
            <Button
              onClick={handleDownload}
              variant="outline"
              size="icon"
              className="h-9 w-9"
              title="Download video file"
            >
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
