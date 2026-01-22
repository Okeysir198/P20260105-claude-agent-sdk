'use client';

import { ReactNode, useRef, useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SwipeActionsProps {
  children: ReactNode;
  onDelete?: () => void;
  className?: string;
  disabled?: boolean;
}

/**
 * Swipe-to-delete action component for mobile.
 * Reveals delete button on left swipe.
 *
 * Features:
 * - Touch swipe detection
 * - Smooth reveal animation
 * - Haptic feedback (if supported)
 * - Minimum touch target (44x44px)
 * - Right-to-left swipe only
 *
 * @example
 * ```tsx
 * <SwipeActions onDelete={() => deleteSession(id)}>
 *   <SessionItem {...props} />
 * </SwipeActions>
 * ```
 */
export function SwipeActions({
  children,
  onDelete,
  className,
  disabled = false,
}: SwipeActionsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [translateX, setTranslateX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const startX = useRef(0);
  const currentX = useRef(0);
  const deleteWidth = 80; // Width of delete action in pixels

  const handleTouchStart = (e: React.TouchEvent) => {
    if (disabled) return;
    const touch = e.touches[0];
    if (!touch) return;

    setIsDragging(true);
    startX.current = touch.clientX;
    if (currentX.current !== undefined) {
      currentX.current = translateX;
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (disabled || !isDragging) return;

    const touch = e.touches[0];
    if (!touch) return;

    const diff = touch.clientX - startX.current;
    const currentXValue = currentX.current ?? 0;
    const newX = Math.min(0, Math.max(-deleteWidth, currentXValue + diff));
    setTranslateX(newX);
  };

  const handleTouchEnd = () => {
    if (disabled || !isDragging) return;
    setIsDragging(false);

    // Snap to open or closed based on position
    if (translateX < -deleteWidth / 2) {
      setTranslateX(-deleteWidth);
    } else {
      setTranslateX(0);
    }
  };

  // Trigger haptic feedback if available
  const triggerHaptic = () => {
    if ('vibrate' in navigator && onDelete) {
      navigator.vibrate(50); // 50ms vibration
    }
  };

  const handleDelete = () => {
    triggerHaptic();
    setTranslateX(0);
    onDelete?.();
  };

  // Reset swipe when component unmounts
  useEffect(() => {
    return () => {
      setTranslateX(0);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-hidden', className)}
      style={{ touchAction: 'pan-y' }} // Allow vertical scrolling
    >
      {/* Delete action (revealed on swipe) */}
      <div
        className="absolute inset-y-0 right-0 flex items-center justify-end bg-error-500"
        style={{
          width: `${deleteWidth}px`,
          transform: `translateX(${translateX + deleteWidth}px)`,
          transition: isDragging ? 'none' : 'transform 0.3s ease-out',
        }}
      >
        <Button
          variant="ghost"
          size="icon"
          onClick={handleDelete}
          className="h-11 w-11 text-white hover:bg-error-600"
          aria-label="Delete"
        >
          <Trash2 className="h-5 w-5" />
        </Button>
      </div>

      {/* Content */}
      <div
        style={{
          transform: `translateX(${translateX}px)`,
          transition: isDragging ? 'none' : 'transform 0.3s ease-out',
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {children}
      </div>
    </div>
  );
}
