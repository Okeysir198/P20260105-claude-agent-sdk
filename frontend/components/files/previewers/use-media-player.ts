'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface MediaPlayerState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
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
  handleDownload: () => void;
  formatTime: (seconds: number) => string;
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

  useEffect(() => {
    if (content instanceof Blob) {
      const url = URL.createObjectURL(content);
      setMediaUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [content]);

  const togglePlayPause = useCallback(() => {
    const el = mediaRef.current;
    if (!el) return;
    if (isPlaying) {
      el.pause();
    } else {
      el.play();
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  const handleTimeUpdate = useCallback(() => {
    if (mediaRef.current) {
      setCurrentTime(mediaRef.current.currentTime);
    }
  }, []);

  const handleLoadedMetadata = useCallback(() => {
    if (mediaRef.current) {
      setDuration(mediaRef.current.duration);
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

  const handleDownload = useCallback(() => {
    if (content instanceof Blob) {
      const url = URL.createObjectURL(content);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(url);
    }
  }, [content, fileName]);

  return {
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
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
