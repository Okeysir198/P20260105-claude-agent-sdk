'use client';

import { ReactNode, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  className?: string;
  maxHeight?: string;
}

/**
 * Mobile bottom sheet component for responsive design.
 * Slides up from bottom on mobile devices.
 *
 * Features:
 * - Smooth slide-up animation
 * - Backdrop dim overlay
 * - Safe area insets for notched devices
 * - Touch-friendly close button (44x44px min)
 * - Prevents body scroll when open
 *
 * @example
 * ```tsx
 * <BottomSheet isOpen={showSidebar} onClose={() => setShowSidebar(false)}>
 *   <SessionList />
 * </BottomSheet>
 * ```
 */
export function BottomSheet({
  isOpen,
  onClose,
  children,
  title,
  className,
  maxHeight = '85vh',
}: BottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null);

  // Prevent body scroll when sheet is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 md:hidden"
      onClick={handleBackdropClick}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in" />

      {/* Sheet */}
      <div
        ref={sheetRef}
        className={cn(
          'absolute bottom-0 left-0 right-0',
          'bg-surface-secondary rounded-t-3xl shadow-2xl',
          'animate-slide-up',
          'max-h-[85vh] flex flex-col',
          className
        )}
        style={{ maxHeight }}
      >
        {/* Handle bar for drag indication */}
        <div className="flex justify-center pt-3 pb-1 shrink-0">
          <div className="w-10 h-1 bg-text-tertiary/30 rounded-full" />
        </div>

        {/* Header with title and close button */}
        {title && (
          <div className="flex items-center justify-between px-4 py-3 border-b border-border-primary shrink-0">
            <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-11 w-11 text-text-secondary"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        )}

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          {children}
        </div>

        {/* Safe area bottom padding for notched devices */}
        <div className="safe-bottom shrink-0" />
      </div>
    </div>
  );
}
