'use client';

import { ReactNode, useRef, useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { RefreshCw } from 'lucide-react';

interface PullToRefreshProps {
  children: ReactNode;
  onRefresh: () => Promise<void> | void;
  className?: string;
  threshold?: number;
  disabled?: boolean;
}

/**
 * Pull-to-refresh component for mobile lists.
 * Triggers refresh on downward pull gesture.
 *
 * Features:
 * - Touch pull detection
 * - Visual feedback indicator
 * - Configurable threshold
 * - Loading state
 * - Prevents over-refreshing with cooldown
 *
 * @example
 * ```tsx
 * <PullToRefresh onRefresh={async () => await fetchSessions()}>
 *   <SessionList />
 * </PullToRefresh>
 * ```
 */
export function PullToRefresh({
  children,
  onRefresh,
  className,
  threshold = 80,
  disabled = false,
}: PullToRefreshProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const startY = useRef(0);

  // Handle touch start
  const handleTouchStart = (e: React.TouchEvent) => {
    if (disabled || isRefreshing) return;

    const container = containerRef.current;
    if (!container) return;

    const { scrollTop } = container;
    const touch = e.touches[0];
    // Only trigger if at top of scroll
    if (scrollTop === 0 && touch) {
      startY.current = touch.clientY;
      setIsDragging(true);
    }
  };

  // Handle touch move
  const handleTouchMove = (e: React.TouchEvent) => {
    if (disabled || isRefreshing || !isDragging) return;

    const touch = e.touches[0];
    if (!touch) return;

    const currentTouchY = touch.clientY;
    const diff = currentTouchY - startY.current;

    // Only allow pulling down (positive diff)
    if (diff > 0) {
      // Add resistance for more natural feel
      const resistance = 0.4;
      const newDistance = Math.min(diff * resistance, threshold * 1.5);
      setPullDistance(newDistance);
    }
  };

  // Handle touch end
  const handleTouchEnd = async () => {
    if (disabled || isRefreshing || !isDragging) return;

    setIsDragging(false);

    // Trigger refresh if threshold exceeded
    if (pullDistance >= threshold) {
      setIsRefreshing(true);
      setPullDistance(threshold);

      try {
        await onRefresh();
      } finally {
        // Animate back after refresh
        setTimeout(() => {
          setIsRefreshing(false);
          setPullDistance(0);
        }, 300);
      }
    } else {
      // Snap back if threshold not met
      setPullDistance(0);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      setPullDistance(0);
      setIsRefreshing(false);
      setIsDragging(false);
    };
  }, []);

  const pullProgress = Math.min(pullDistance / threshold, 1);
  const showIndicator = pullDistance > 20 || isRefreshing;

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-hidden', className)}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Pull indicator */}
      {showIndicator && (
        <div
          className="absolute left-0 right-0 flex items-center justify-center bg-surface-secondary/80 backdrop-blur-sm border-b border-border-primary z-10"
          style={{
            height: `${Math.min(pullDistance, threshold)}px`,
            opacity: pullProgress,
            transition: isDragging ? 'none' : 'all 0.3s ease-out',
          }}
        >
          <div
            className={cn(
              'text-text-secondary',
              isRefreshing && 'animate-spin'
            )}
            style={{
              transform: `rotate(${pullProgress * 360}deg)`,
              transition: isDragging ? 'none' : 'transform 0.3s ease-out',
            }}
          >
            <RefreshCw className="h-5 w-5" />
          </div>
        </div>
      )}

      {/* Content */}
      <div
        style={{
          transform: isDragging ? `translateY(${pullDistance}px)` : 'translateY(0)',
          transition: isDragging ? 'none' : 'transform 0.3s ease-out',
        }}
      >
        {children}
      </div>
    </div>
  );
}
