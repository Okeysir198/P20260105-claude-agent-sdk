'use client';

import { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ToolUseMessage as ToolUseMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';
import { chevronVariants, fadeVariants } from '@/lib/animations';

interface ToolUseMessageProps {
  message: ToolUseMessageType;
  className?: string;
}

export const ToolUseMessage = memo(function ToolUseMessage({
  message,
  className
}: ToolUseMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const inputJson = JSON.stringify(message.input, null, 2);
  const isLongInput = inputJson.length > 200;

  return (
    <div className={cn(
      'max-w-[90%] mx-auto',
      'bg-warning-50 dark:bg-warning-700/20',
      'border border-warning-500/30',
      'rounded-xl',
      'overflow-hidden',
      className
    )}>
      {/* Header */}
      <div className={cn(
        'flex items-center gap-2 px-4 py-2',
        'bg-warning-100 dark:bg-warning-700/30',
        'border-b border-warning-500/30'
      )}>
        {/* Wrench Icon */}
        <svg
          className="w-4 h-4 text-warning-600 dark:text-warning-400"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>

        {/* Tool name badge */}
        <span className={cn(
          'px-2 py-0.5',
          'text-xs font-medium',
          'bg-warning-200 dark:bg-warning-600/40',
          'text-warning-700 dark:text-warning-300',
          'rounded-md'
        )}>
          {message.toolName}
        </span>

        <span className="text-xs text-warning-600 dark:text-warning-400">
          Tool invocation
        </span>

        {/* Expand/collapse button for long inputs */}
        {isLongInput && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(
              'ml-auto flex items-center gap-1 text-xs',
              'text-warning-600 dark:text-warning-400',
              'hover:text-warning-700 dark:hover:text-warning-300',
              'transition-colors'
            )}
          >
            <motion.svg
              className="w-3 h-3"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              variants={chevronVariants}
              animate={isExpanded ? 'expanded' : 'collapsed'}
              transition={{ duration: 0.2 }}
            >
              <path d="m6 9 6 6 6-6" />
            </motion.svg>
            {isExpanded ? 'Collapse' : 'Expand'}
          </button>
        )}
      </div>

      {/* Input JSON */}
      <div className="p-3 relative overflow-hidden">
        <motion.div
          initial={false}
          animate={{
            height: !isExpanded && isLongInput ? 96 : 'auto'
          }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
        >
          <pre className={cn(
            'text-xs font-mono',
            'text-warning-800 dark:text-warning-200',
            'overflow-x-auto'
          )}>
            <code>{inputJson}</code>
          </pre>
        </motion.div>

        {/* Gradient fade for collapsed long content */}
        <AnimatePresence>
          {!isExpanded && isLongInput && (
            <motion.div
              variants={fadeVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className={cn(
                'absolute bottom-0 left-0 right-0 h-8',
                'bg-gradient-to-t from-warning-50 dark:from-warning-700/20 to-transparent',
                'pointer-events-none'
              )}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
});
