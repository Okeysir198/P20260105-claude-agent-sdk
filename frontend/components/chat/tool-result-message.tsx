'use client';

import { memo } from 'react';
import type { ToolResultMessage as ToolResultMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';
import { ExpandablePanel } from './expandable-panel';
import { CheckCircle2, XCircle } from 'lucide-react';

interface ToolResultMessageProps {
  message: ToolResultMessageType;
  className?: string;
}

export const ToolResultMessage = memo(function ToolResultMessage({
  message,
  className
}: ToolResultMessageProps) {
  const isError = message.isError;

  const header = (
    <>
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
      <span className={cn(
        'text-xs font-medium',
        isError ? 'text-error-700 dark:text-error-300' : 'text-success-700 dark:text-success-300'
      )}>
        {isError ? 'Error' : 'Result'}
      </span>
    </>
  );

  return (
    <div className={cn('flex justify-start', className)}>
      {/* Spacer to align with assistant message avatar (w-8 + gap-3 = 44px) */}
      <div className="w-8 flex-shrink-0" />
      <div className="w-3 flex-shrink-0" />

      <div className="max-w-[85%]">
        <ExpandablePanel header={header}>
          <pre className={cn(
            'text-xs font-mono whitespace-pre-wrap break-words',
            'text-text-secondary',
            'bg-surface-primary dark:bg-surface-inverse/5',
            'rounded-lg p-3',
            'max-h-60 overflow-y-auto'
          )}>
            <code>{message.content}</code>
          </pre>
        </ExpandablePanel>
      </div>
    </div>
  );
});
