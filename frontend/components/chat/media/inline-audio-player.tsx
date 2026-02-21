'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import { Play, Pause, Mic, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

interface InlineAudioPlayerProps {
  src: string;
  filename?: string;
  mimeType?: string;
  /** Compact mode for attachment preview in chat input */
  compact?: boolean;
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds) || isNaN(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/** Generate deterministic pseudo-waveform bars from a string seed */
function generateWaveformBars(seed: string, count: number): number[] {
  const bars: number[] = [];
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash << 5) - hash + seed.charCodeAt(i)) | 0;
  }
  for (let i = 0; i < count; i++) {
    hash = ((hash << 5) - hash + i * 7 + 13) | 0;
    const normalized = (Math.abs(hash) % 80 + 20) / 100; // 0.2–1.0
    bars.push(normalized);
  }
  return bars;
}

export function InlineAudioPlayer({ src, filename, mimeType, compact }: InlineAudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(false);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
    } else {
      audio.play().catch((err) => {
        console.error('Audio playback failed:', err);
        setError(true);
        toast.error('Unable to play audio — format may not be supported by this browser');
      });
    }
  }, [playing]);

  const handleBarClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const ratio = x / rect.width;
    audio.currentTime = ratio * duration;
    setCurrentTime(ratio * duration);
  }, [duration]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoadedMetadata = () => setDuration(audio.duration);
    const onEnded = () => { setPlaying(false); setCurrentTime(0); };
    const onError = () => setError(true);

    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('error', onError);

    return () => {
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('error', onError);
    };
  }, []);

  const progress = duration > 0 ? currentTime / duration : 0;
  const barCount = compact ? 20 : 32;
  const bars = generateWaveformBars(filename || src, barCount);

  if (compact) {
    return (
      <div className="flex items-center gap-2 w-full">
        <audio ref={audioRef} preload="metadata">
          <source src={src} type={mimeType || 'audio/webm'} />
        </audio>
        <button
          type="button"
          onClick={togglePlay}
          disabled={error}
          className={`flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full transition-colors ${
            error ? 'bg-destructive/10 cursor-not-allowed' : 'bg-primary/10 hover:bg-primary/20'
          }`}
          aria-label={error ? 'Playback error' : playing ? 'Pause' : 'Play'}
        >
          {error ? (
            <AlertCircle className="h-3.5 w-3.5 text-destructive" />
          ) : playing ? (
            <Pause className="h-3.5 w-3.5 text-primary" />
          ) : (
            <Play className="h-3.5 w-3.5 text-primary ml-0.5" />
          )}
        </button>
        <div
          className="flex-1 flex items-center gap-[2px] h-6 cursor-pointer"
          onClick={handleBarClick}
          role="slider"
          aria-label="Audio progress"
          aria-valuenow={Math.round(progress * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          {bars.map((h, i) => {
            const barProgress = i / bars.length;
            const isPlayed = barProgress < progress;
            return (
              <div
                key={i}
                className={`flex-1 rounded-full transition-colors duration-75 ${
                  isPlayed ? 'bg-primary' : 'bg-muted-foreground/25'
                }`}
                style={{ height: `${h * 100}%` }}
              />
            );
          })}
        </div>
        <span className="flex-shrink-0 text-[10px] text-muted-foreground font-mono tabular-nums min-w-[28px] text-right">
          {formatTime(playing ? currentTime : duration)}
        </span>
      </div>
    );
  }

  return (
    <div className="w-full sm:w-auto sm:max-w-[320px] flex items-center gap-2.5 pl-2 pr-3 py-2 rounded-2xl bg-muted/50 border border-border/20">
      <audio ref={audioRef} src={src} preload="metadata">
        {mimeType && <source src={src} type={mimeType} />}
      </audio>

      {/* Play/Pause button */}
      <button
        type="button"
        onClick={togglePlay}
        disabled={error}
        className={`flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-full transition-colors ${
          error ? 'bg-destructive/10 cursor-not-allowed' : 'bg-primary/15 hover:bg-primary/25'
        }`}
        aria-label={error ? 'Playback error' : playing ? 'Pause' : 'Play'}
      >
        {error ? (
          <AlertCircle className="h-4 w-4 text-destructive" />
        ) : playing ? (
          <Pause className="h-4 w-4 text-primary" />
        ) : (
          <Play className="h-4 w-4 text-primary ml-0.5" />
        )}
      </button>

      {/* Waveform progress */}
      <div className="flex-1 flex flex-col gap-1 min-w-0">
        <div
          className="flex items-center gap-[2px] h-7 cursor-pointer"
          onClick={handleBarClick}
          role="slider"
          aria-label="Audio progress"
          aria-valuenow={Math.round(progress * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          {bars.map((h, i) => {
            const barProgress = i / bars.length;
            const isPlayed = barProgress < progress;
            return (
              <div
                key={i}
                className={`flex-1 rounded-full transition-colors duration-75 ${
                  isPlayed ? 'bg-primary' : 'bg-muted-foreground/20'
                }`}
                style={{ height: `${h * 100}%` }}
              />
            );
          })}
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-muted-foreground font-mono tabular-nums">
            {formatTime(currentTime)}
          </span>
          <div className="flex items-center gap-1">
            <Mic className="h-2.5 w-2.5 text-muted-foreground/50" />
            <span className="text-[10px] text-muted-foreground font-mono tabular-nums">
              {formatTime(duration)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
