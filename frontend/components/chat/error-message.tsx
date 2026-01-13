'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorMessage = memo(function ErrorMessage({
  message,
  onRetry,
  className
}: ErrorMessageProps) {
  return (
    <div className={cn(
      'max-w-[90%] mx-auto',
      'bg-error-50 dark:bg-error-700/20',
      'border border-error-500/50',
      'rounded-xl',
      'p-4',
      className
    )}>
      <div className="flex items-start gap-3">
        {/* Error Icon */}
        <div className={cn(
          'flex-shrink-0 w-8 h-8',
          'rounded-full',
          'bg-error-100 dark:bg-error-700/40',
          'flex items-center justify-center',
          'text-error-600 dark:text-error-400'
        )}>
          <svg
            className="w-5 h-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h4 className={cn(
            'text-sm font-medium',
            'text-error-800 dark:text-error-200'
          )}>
            Something went wrong
          </h4>
          <p className={cn(
            'mt-1 text-sm',
            'text-error-700 dark:text-error-300',
            'break-words'
          )}>
            {message}
          </p>

          {/* Retry button */}
          {onRetry && (
            <button
              onClick={onRetry}
              className={cn(
                'mt-3 px-4 py-2',
                'text-sm font-medium',
                'bg-error-100 dark:bg-error-700/40',
                'text-error-700 dark:text-error-300',
                'rounded-lg',
                'hover:bg-error-200 dark:hover:bg-error-700/60',
                'transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-error-500 focus:ring-offset-2'
              )}
            >
              <span className="flex items-center gap-2">
                {/* Retry Icon */}
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                  <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
                  <path d="M16 21h5v-5" />
                </svg>
                Try again
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
});
