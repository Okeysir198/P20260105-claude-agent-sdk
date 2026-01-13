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
          'inline-block w-2 h-5',
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
      className={cn('flex items-center gap-1', className)}
      aria-label="Typing"
    >
      {dotDelays.map((delay, index) => (
        <motion.span
          key={index}
          className={cn(
            'w-2 h-2 rounded-full',
            'bg-claude-orange-400'
          )}
          variants={typingDotVariants}
          initial="initial"
          animate="animate"
          transition={{
            delay,
            duration: 0.6,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
});
