'use client';

/**
 * Ambient Glow Component
 *
 * 2026 Design Pattern: Ambient AI Interface
 *
 * Provides a subtle pulsing glow indicator when AI is thinking or processing.
 * Uses gradient backgrounds with soft animations to indicate activity without
 * being distracting.
 *
 * Features:
 * - Subtle pulsing glow effect
 * - Gradient color transitions
 * - Configurable intensity and size
 * - Smooth spring animations
 *
 * @module components/animations/ambient-glow
 */

import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { ambientGlowVariants, gradientActivityVariants } from '@/lib/animations';

interface AmbientGlowProps {
  /** Whether AI is actively thinking/processing */
  isActive: boolean;
  /** Size of the glow effect */
  size?: 'sm' | 'md' | 'lg';
  /** Color scheme for the glow */
  variant?: 'orange' | 'blue' | 'purple' | 'green';
  /** Position of the glow relative to container */
  position?: 'center' | 'top' | 'bottom';
  /** Additional CSS classes */
  className?: string;
  /** Whether to show gradient background instead of radial glow */
  useGradient?: boolean;
}

const sizeClasses = {
  sm: 'w-16 h-16',
  md: 'w-24 h-24',
  lg: 'w-32 h-32',
};

const gradientSizeClasses = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
};

const colorClasses = {
  orange: 'bg-claude-orange-500',
  blue: 'bg-info-500',
  purple: 'bg-purple-500',
  green: 'bg-success-500',
};

const gradientClasses = {
  orange: 'from-claude-orange-500 via-claude-orange-400 to-claude-orange-500',
  blue: 'from-info-500 via-info-400 to-info-500',
  purple: 'from-purple-500 via-purple-400 to-purple-500',
  green: 'from-success-500 via-success-400 to-success-500',
};

const positionClasses = {
  center: 'items-center justify-center',
  top: 'items-start justify-center pt-4',
  bottom: 'items-end justify-center pb-4',
};

/**
 * Ambient glow indicator component for AI thinking states
 *
 * @example
 * ```tsx
 * <AmbientGlow
 *   isActive={isStreaming}
 *   size="md"
 *   variant="orange"
 *   position="top"
 * />
 * ```
 */
export function AmbientGlow({
  isActive,
  size = 'md',
  variant = 'orange',
  position = 'center',
  className,
  useGradient = false,
}: AmbientGlowProps) {
  // Gradient background variant
  if (useGradient) {
    return (
      <AnimatePresence>
        {isActive && (
          <motion.div
            className={cn(
              'absolute inset-0 w-full bg-gradient-to-r',
              gradientClasses[variant],
              gradientSizeClasses[size],
              'opacity-30',
              'bg-[length:200%_100%]',
              className
            )}
            variants={gradientActivityVariants}
            initial="inactive"
            animate="active"
            exit="inactive"
            style={{
              backgroundSize: '200% 100%',
            }}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>
    );
  }

  // Radial glow variant
  return (
    <AnimatePresence>
      {isActive && (
        <motion.div
          className={cn(
            'absolute rounded-full blur-xl',
            'pointer-events-none',
            colorClasses[variant],
            sizeClasses[size],
            positionClasses[position],
            className
          )}
          variants={ambientGlowVariants}
          initial="inactive"
          animate="active"
          exit="inactive"
          aria-hidden="true"
        />
      )}
    </AnimatePresence>
  );
}

/**
 * Compact ambient glow for inline indicators
 */
interface InlineGlowProps {
  isActive: boolean;
  variant?: 'orange' | 'blue' | 'purple' | 'green';
  className?: string;
}

export function InlineGlow({
  isActive,
  variant = 'orange',
  className,
}: InlineGlowProps) {
  return (
    <AnimatePresence>
      {isActive && (
        <motion.div
          className={cn(
            'relative inline-flex items-center',
            className
          )}
          aria-hidden="true"
        >
          <motion.div
            className={cn(
              'absolute w-2 h-2 rounded-full blur-sm',
              colorClasses[variant]
            )}
            variants={ambientGlowVariants}
            initial="inactive"
            animate="active"
            exit="inactive"
          />
          <div className="w-2 h-2 rounded-full bg-current" />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/**
 * Activity bar for indicating processing state
 */
interface ActivityBarProps {
  isActive: boolean;
  variant?: 'orange' | 'blue' | 'purple' | 'green';
  className?: string;
}

export function ActivityBar({
  isActive,
  variant = 'orange',
  className,
}: ActivityBarProps) {
  return (
    <AnimatePresence>
      {isActive && (
        <motion.div
          className={cn(
            'h-0.5 w-full rounded-full overflow-hidden',
            'bg-gradient-to-r',
            gradientClasses[variant],
            'bg-[length:200%_100%]',
            className
          )}
          variants={gradientActivityVariants}
          initial="inactive"
          animate="active"
          exit="inactive"
          style={{
            backgroundSize: '200% 100%',
          }}
          aria-hidden="true"
        />
      )}
    </AnimatePresence>
  );
}
