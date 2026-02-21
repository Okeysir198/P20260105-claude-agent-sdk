'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface MediaPlayerState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  error: string | null;
}

interface MediaPlayerActions {
  mediaUrl: string;
  mediaRef: React.RefObject<HTMLAudioElement | HTMLVideoElement | null>;
  togglePlayPause: () => void;
  handleTimeUpdate: () => void;
  handleLoadedMetadata: () => void;
  handleSeek: (value: number[]) => void;
  handleVolumeChange: (value: number[]) => void;
  toggleMute: () => void;
  handleEnded: () => void;
  handlePlay: () => void;
  handlePause: () => void;
  handleError: () => void;
  handleDownload: () => void;
  formatTime: (seconds: number) => string;
}

/**
 * Infer MIME type from filename extension.
 * Used as fallback when Blob has no type or generic type.
 */
function inferMimeType(fileName: string): string | undefined {
  const ext = fileName.split('.').pop()?.toLowerCase();
  const mimeMap: Record<string, string> = {
    wav: 'audio/wav',
    mp3: 'audio/mpeg',
    ogg: 'audio/ogg',
    m4a: 'audio/mp4',
    aac: 'audio/aac',
    flac: 'audio/flac',
    opus: 'audio/opus',
    webm: 'audio/webm',
    mp4: 'video/mp4',
    mov: 'video/quicktime',
    avi: 'video/x-msvideo',
    mkv: 'video/x-matroska',
  };
  return ext ? mimeMap[ext] : undefined;
}

export function useMediaPlayer(
  content: string | Blob,
  fileName: string
): MediaPlayerState & MediaPlayerActions {
  const mediaRef = useRef<HTMLAudioElement | HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [mediaUrl, setMediaUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (content instanceof Blob) {
      // Ensure blob has correct MIME type for browser playback.
      // If the blob type is missing or generic, re-create with inferred type.
      let blob = content;
      const inferredType = inferMimeType(fileName);
      if (inferredType && (!blob.type || blob.type === 'application/octet-stream')) {
        blob = new Blob([content], { type: inferredType });
      }

      const url = URL.createObjectURL(blob);
      setMediaUrl(url);
      setError(null);
      return () => URL.revokeObjectURL(url);
    } else if (typeof content === 'string' && content) {
      // String URL (e.g., download URL) — use directly
      setMediaUrl(content);
      setError(null);
    }
  }, [content, fileName]);

  const togglePlayPause = useCallback(async () => {
    const el = mediaRef.current;
    if (!el) return;
    if (isPlaying) {
      el.pause();
      setIsPlaying(false);
    } else {
      try {
        await el.play();
        setIsPlaying(true);
      } catch (err) {
        console.warn('Media play failed:', err);
        setIsPlaying(false);
      }
    }
  }, [isPlaying]);

  const handleTimeUpdate = useCallback(() => {
    if (mediaRef.current) {
      setCurrentTime(mediaRef.current.currentTime);
    }
  }, []);

  const handleLoadedMetadata = useCallback(() => {
    if (mediaRef.current) {
      setDuration(mediaRef.current.duration);
      setError(null);
    }
  }, []);

  const handleSeek = useCallback((value: number[]) => {
    const newTime = value[0];
    if (mediaRef.current) {
      mediaRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  }, []);

  const handleVolumeChange = useCallback((value: number[]) => {
    const newVolume = value[0];
    if (mediaRef.current) {
      mediaRef.current.volume = newVolume;
      setVolume(newVolume);
      setIsMuted(newVolume === 0);
    }
  }, []);

  const toggleMute = useCallback(() => {
    const el = mediaRef.current;
    if (!el) return;
    if (isMuted) {
      el.volume = volume || 1;
      setIsMuted(false);
    } else {
      el.volume = 0;
      setIsMuted(true);
    }
  }, [isMuted, volume]);

  const handleEnded = useCallback(() => setIsPlaying(false), []);
  const handlePlay = useCallback(() => setIsPlaying(true), []);
  const handlePause = useCallback(() => setIsPlaying(false), []);

  const handleError = useCallback(() => {
    setIsPlaying(false);
    setError('Unable to play this audio file. The format may not be supported by your browser.');
  }, []);

  const handleDownload = useCallback(() => {
    const a = document.createElement('a');
    if (content instanceof Blob) {
      const url = URL.createObjectURL(content);
      a.href = url;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(url);
    } else if (typeof content === 'string' && content) {
      a.href = content;
      a.download = fileName;
      a.click();
    }
  }, [content, fileName]);

  return {
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    error,
    mediaUrl,
    mediaRef,
    togglePlayPause,
    handleTimeUpdate,
    handleLoadedMetadata,
    handleSeek,
    handleVolumeChange,
    toggleMute,
    handleEnded,
    handlePlay,
    handlePause,
    handleError,
    handleDownload,
    formatTime,
  };
}

function formatTime(seconds: number): string {
  if (isNaN(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
