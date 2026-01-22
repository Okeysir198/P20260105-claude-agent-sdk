'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

/**
 * Claude logo SVG component.
 */
function ClaudeLogo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 80 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="40"
        cy="40"
        r="36"
        className="fill-claude-orange-100 dark:fill-claude-orange-900/30"
      />
      <path
        d="M40 16C26.745 16 16 26.745 16 40C16 53.255 26.745 64 40 64C53.255 64 64 53.255 64 40C64 26.745 53.255 16 40 16Z"
        className="fill-claude-orange-500"
        fillOpacity="0.2"
      />
      <path
        d="M28 40C28 33.373 33.373 28 40 28C46.627 28 52 33.373 52 40C52 46.627 46.627 52 40 52"
        className="stroke-claude-orange-600 dark:stroke-claude-orange-500"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <circle
        cx="40"
        cy="40"
        r="6"
        className="fill-claude-orange-600 dark:fill-claude-orange-500"
      />
    </svg>
  );
}

interface WelcomeScreenProps {
  className?: string;
}

export const WelcomeScreen = memo(function WelcomeScreen({ className }: WelcomeScreenProps) {
  return (
    <div className={cn('flex-1 flex flex-col items-center justify-center px-4', className)}>
      {/* Main content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="flex flex-col items-center text-center max-w-md"
      >
        {/* Logo */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <ClaudeLogo className="w-20 h-20 mb-6" />
        </motion.div>

        {/* Title */}
        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-2xl font-serif text-text-primary mb-2"
        >
          Hello, I&apos;m Claude
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="text-text-secondary text-base mb-8 leading-relaxed"
        >
          I&apos;m an AI assistant created by Anthropic. I can help you with analysis, coding, writing, and more.
        </motion.p>

        {/* Suggestion chips */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex flex-wrap gap-2 justify-center"
        >
          {[
            'Explain a concept',
            'Help with code',
            'Write content',
            'Analyze data',
          ].map((suggestion) => (
            <span
              key={suggestion}
              className={cn(
                'px-3 py-1.5 text-sm rounded-full',
                'bg-surface-secondary border border-border-primary',
                'text-text-secondary',
                'transition-colors hover:bg-surface-tertiary hover:text-text-primary cursor-default'
              )}
            >
              {suggestion}
            </span>
          ))}
        </motion.div>
      </motion.div>

      {/* Footer */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.6 }}
        className="absolute bottom-24 text-xs text-text-tertiary"
      >
        Type a message below to start the conversation
      </motion.p>
    </div>
  );
});
