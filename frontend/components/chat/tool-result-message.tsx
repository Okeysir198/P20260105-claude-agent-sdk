'use client';

import { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ToolResultMessage as ToolResultMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';
import { chevronVariants } from '@/lib/animations';
import { CheckCircle2, XCircle, ChevronDown } from 'lucide-react';

interface ToolResultMessageProps {
  message: ToolResultMessageType;
  className?: string;
}

export const ToolResultMessage = memo(function ToolResultMessage({
  message,
  className
}: ToolResultMessageProps) {
  // Collapsed by default
  const [isExpanded, setIsExpanded] = useState(false);
  const isError = message.isError;

  return (
    <div className={cn('flex justify-start', className)}>
      {/* Spacer to align with assistant message avatar (w-8 + gap-3 = 44px) */}
      <div className="w-8 flex-shrink-0" />
      <div className="w-3 flex-shrink-0" />

      <div className={cn(
        'max-w-[85%]',
        'border border-border-primary',
        'rounded-lg',
        'overflow-hidden'
      )}>
        {/* Header - clickable to expand/collapse */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            'flex items-center gap-2 px-3 py-2 w-full text-left',
            'bg-surface-tertiary dark:bg-surface-tertiary/50',
            'border-b border-border-primary',
            'hover:bg-surface-tertiary/80 dark:hover:bg-surface-tertiary/70',
            'transition-colors cursor-pointer'
          )}
        >
          {/* Status icon */}
          <div className={cn(
            'w-5 h-5 rounded-md flex items-center justify-center',
            isError
              ? 'bg-error-100 dark:bg-error-900/30'
              : 'bg-success-100 dark:bg-success-900/30'
          )}>
            {isError ? (
              <XCircle className="w-3 h-3 text-error-600 dark:text-error-400" />
            ) : (
              <CheckCircle2 className="w-3 h-3 text-success-600 dark:text-success-400" />
            )}
          </div>

          {/* Status text */}
          <span className={cn(
            'text-xs font-medium',
            isError ? 'text-error-700 dark:text-error-300' : 'text-success-700 dark:text-success-300'
          )}>
            {isError ? 'Error' : 'Result'}
          </span>

          {/* Expand/collapse chevron */}
          <motion.div
            className="ml-auto"
            variants={chevronVariants}
            animate={isExpanded ? 'expanded' : 'collapsed'}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-4 h-4 text-text-tertiary" />
          </motion.div>
        </button>

        {/* Content - only shown when expanded */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div className="px-3 pb-3">
                <pre className={cn(
                  'text-xs font-mono whitespace-pre-wrap break-words',
                  'text-text-secondary',
                  'bg-surface-primary dark:bg-surface-inverse/5',
                  'rounded-lg p-3',
                  'max-h-60 overflow-y-auto'
                )}>
                  <code>{message.content}</code>
                </pre>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
});
