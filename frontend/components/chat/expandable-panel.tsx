'use client';

import { useState, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { chevronVariants, toolExpandVariants } from '@/lib/animations';
import { ChevronDown } from 'lucide-react';

interface ExpandablePanelProps {
  /** Header content (icon and title) */
  header: ReactNode;
  /** Expandable content */
  children: ReactNode;
  /** Initial expanded state (default: false) */
  defaultExpanded?: boolean;
  /** Additional class names for the container */
  className?: string;
}

/**
 * Expandable panel component for tool messages.
 *
 * @example
 * <ExpandablePanel
 *   header={
 *     <>
 *       <div className="w-5 h-5 rounded-md bg-warning-100 flex items-center justify-center">
 *         <Wrench className="w-3 h-3 text-warning-600" />
 *       </div>
 *       <span className="text-xs font-medium text-text-primary">{toolName}</span>
 *     </>
 *   }
 * >
 *   <pre><code>{content}</code></pre>
 * </ExpandablePanel>
 */
export function ExpandablePanel({
  header,
  children,
  defaultExpanded = false,
  className,
}: ExpandablePanelProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={cn(
      'border border-border-primary rounded-lg overflow-hidden',
      className
    )}>
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
        {header}
        <motion.div
          className="ml-auto"
          variants={chevronVariants}
          animate={isExpanded ? 'expanded' : 'collapsed'}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4 text-text-tertiary" />
        </motion.div>
      </button>

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
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
