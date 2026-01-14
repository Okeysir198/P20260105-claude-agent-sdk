'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { typingDotVariants, cursorVariants } from '@/lib/animations';

interface TypingIndicatorProps {
  className?: string;
  variant?: 'dots' | 'cursor';
}

/**
 * Stagger delays for the three dots
 */
const dotDelays = [0, 0.15, 0.3];

export const TypingIndicator = memo(function TypingIndicator({
  className,
  variant = 'dots'
}: TypingIndicatorProps) {
  if (variant === 'cursor') {
    return (
      <motion.span
        className={cn(
          'inline-block w-0.5 h-5 rounded-full',
          'bg-claude-orange-500',
          className
        )}
        variants={cursorVariants}
        initial="initial"
        animate="animate"
        aria-label="Typing"
      />
    );
  }

  // Default: bouncing dots with framer-motion
  return (
    <div
      className={cn('flex items-center gap-1.5 py-1', className)}
      aria-label="Claude is typing"
    >
      {dotDelays.map((delay, index) => (
        <motion.div
          key={index}
          className={cn(
            'w-2 h-2 rounded-full',
            'bg-claude-orange-500 dark:bg-claude-orange-400',
            'shadow-sm'
          )}
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            delay,
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
});
