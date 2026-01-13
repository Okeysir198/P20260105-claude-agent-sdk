'use client';

import { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ToolResultMessage as ToolResultMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';
import { chevronVariants, fadeVariants } from '@/lib/animations';

interface ToolResultMessageProps {
  message: ToolResultMessageType;
  className?: string;
}

export const ToolResultMessage = memo(function ToolResultMessage({
  message,
  className
}: ToolResultMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isLongContent = message.content.length > 300;
  const isError = message.isError;

  return (
    <div className={cn(
      'max-w-[90%] mx-auto',
      isError
        ? 'bg-error-50 dark:bg-error-700/20 border-error-500/30'
        : 'bg-success-50 dark:bg-success-700/20 border-success-500/30',
      'border',
      'rounded-xl',
      'overflow-hidden',
      className
    )}>
      {/* Header */}
      <div className={cn(
        'flex items-center gap-2 px-4 py-2',
        isError
          ? 'bg-error-100 dark:bg-error-700/30 border-b border-error-500/30'
          : 'bg-success-100 dark:bg-success-700/30 border-b border-success-500/30'
      )}>
        {/* Status Icon */}
        {isError ? (
          // X Icon for error
          <svg
            className="w-4 h-4 text-error-600 dark:text-error-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="m15 9-6 6" />
            <path d="m9 9 6 6" />
          </svg>
        ) : (
          // Check Icon for success
          <svg
            className="w-4 h-4 text-success-600 dark:text-success-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="m9 12 2 2 4-4" />
          </svg>
        )}

        <span className={cn(
          'text-xs font-medium',
          isError
            ? 'text-error-700 dark:text-error-300'
            : 'text-success-700 dark:text-success-300'
        )}>
          {isError ? 'Tool Error' : 'Tool Result'}
        </span>

        {/* Tool use ID reference */}
        {message.toolUseId && (
          <span className={cn(
            'text-xs',
            isError
              ? 'text-error-500 dark:text-error-400'
              : 'text-success-500 dark:text-success-400'
          )}>
            #{message.toolUseId.slice(-8)}
          </span>
        )}

        {/* Expand/collapse button for long content */}
        {isLongContent && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(
              'ml-auto flex items-center gap-1 text-xs',
              isError
                ? 'text-error-600 dark:text-error-400 hover:text-error-700 dark:hover:text-error-300'
                : 'text-success-600 dark:text-success-400 hover:text-success-700 dark:hover:text-success-300',
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

      {/* Content */}
      <div className="p-3 relative overflow-hidden">
        <motion.div
          initial={false}
          animate={{
            height: !isExpanded && isLongContent ? 128 : 'auto'
          }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
        >
          <pre className={cn(
            'text-xs font-mono whitespace-pre-wrap break-words',
            isError
              ? 'text-error-800 dark:text-error-200'
              : 'text-success-800 dark:text-success-200'
          )}>
            <code>{message.content}</code>
          </pre>
        </motion.div>

        {/* Gradient fade for collapsed long content */}
        <AnimatePresence>
          {!isExpanded && isLongContent && (
            <motion.div
              variants={fadeVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className={cn(
                'absolute bottom-0 left-0 right-0 h-8',
                isError
                  ? 'bg-gradient-to-t from-error-50 dark:from-error-700/20 to-transparent'
                  : 'bg-gradient-to-t from-success-50 dark:from-success-700/20 to-transparent',
                'pointer-events-none'
              )}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
});
