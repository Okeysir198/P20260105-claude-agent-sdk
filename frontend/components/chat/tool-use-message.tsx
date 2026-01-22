'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import type { ToolUseMessage as ToolUseMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';
import { ExpandablePanel } from './expandable-panel';
import { Wrench } from 'lucide-react';
import { toolUseSpringVariants } from '@/lib/animations';

interface ToolUseMessageProps {
  message: ToolUseMessageType;
  className?: string;
}

const AVATAR_SPACER_WIDTH = 'w-11'; // w-8 avatar + w-3 gap = 44px

export const ToolUseMessage = memo(function ToolUseMessage({
  message,
  className
}: ToolUseMessageProps): React.ReactElement {
  const inputJson = JSON.stringify(message.input, null, 2);

  return (
    <motion.div
      className={cn('flex justify-start', className)}
      variants={toolUseSpringVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
    >
      <div className={cn(AVATAR_SPACER_WIDTH, 'flex-shrink-0')} />

      <div className="max-w-[85%]">
        <ExpandablePanel
          header={
            <>
              <div className="w-5 h-5 rounded-md bg-warning-100 dark:bg-warning-900/30 flex items-center justify-center">
                <Wrench className="w-3 h-3 text-warning-600 dark:text-warning-400" />
              </div>
              <span className="text-xs font-medium text-text-primary">
                {message.toolName}
              </span>
            </>
          }
        >
          <pre className={cn(
            'text-xs font-mono text-text-secondary',
            'bg-surface-primary dark:bg-surface-inverse/5',
            'rounded-lg p-3 overflow-x-auto'
          )}>
            <code>{inputJson}</code>
          </pre>
        </ExpandablePanel>
      </div>
    </motion.div>
  );
});
