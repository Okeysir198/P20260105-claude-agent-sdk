'use client';

import { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ToolUseMessage as ToolUseMessageType } from '@/types/messages';
import { cn } from '@/lib/utils';
import { chevronVariants, messageItemVariants, toolExpandVariants } from '@/lib/animations';
import { Wrench, ChevronDown } from 'lucide-react';

interface ToolUseMessageProps {
  message: ToolUseMessageType;
  className?: string;
}

const AVATAR_SPACER_WIDTH = 'w-11'; // w-8 avatar + w-3 gap = 44px

function ExpandableHeader({
  isExpanded,
  onToggle,
  children,
}: {
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'flex items-center gap-2 px-3 py-2 w-full text-left',
        'hover:bg-surface-tertiary/70 dark:hover:bg-surface-tertiary/50',
        'transition-colors cursor-pointer'
      )}
    >
      {children}
      <motion.div
        className="ml-auto"
        variants={chevronVariants}
        animate={isExpanded ? 'expanded' : 'collapsed'}
        transition={{ duration: 0.2 }}
      >
        <ChevronDown className="w-4 h-4 text-text-tertiary" />
      </motion.div>
    </button>
  );
}

export const ToolUseMessage = memo(function ToolUseMessage({
  message,
  className
}: ToolUseMessageProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState(false);
  const inputJson = JSON.stringify(message.input, null, 2);

  return (
    <motion.div
      variants={messageItemVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={cn('flex justify-start', className)}
    >
      <div className={cn(AVATAR_SPACER_WIDTH, 'flex-shrink-0')} />

      <div className={cn(
        'max-w-[75%]',
        'bg-surface-tertiary/50 dark:bg-surface-tertiary/30',
        'border border-border-primary rounded-xl overflow-hidden'
      )}>
        <ExpandableHeader
          isExpanded={isExpanded}
          onToggle={() => setIsExpanded(!isExpanded)}
        >
          <div className="w-5 h-5 rounded-md bg-warning-100 dark:bg-warning-900/30 flex items-center justify-center">
            <Wrench className="w-3 h-3 text-warning-600 dark:text-warning-400" />
          </div>
          <span className="text-xs font-medium text-text-primary">
            {message.toolName}
          </span>
        </ExpandableHeader>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              variants={toolExpandVariants}
              initial="collapsed"
              animate="expanded"
              exit="collapsed"
              className="overflow-hidden"
            >
              <div className="px-3 pb-3">
                <pre className={cn(
                  'text-xs font-mono text-text-secondary',
                  'bg-surface-primary dark:bg-surface-inverse/5',
                  'rounded-lg p-3 overflow-x-auto'
                )}>
                  <code>{inputJson}</code>
                </pre>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
});
