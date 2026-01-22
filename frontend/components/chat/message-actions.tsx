'use client';

import { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Copy, Trash2, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MessageActionsProps {
  content: string;
  messageId: string;
  onDelete?: (messageId: string) => void;
  className?: string;
}

function PureMessageActions({ content, messageId, onDelete, className }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = () => {
    onDelete?.(messageId);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.15 }}
        className={cn(
          'flex items-center gap-1',
          className
        )}
      >
        {/* Copy button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleCopy}
          className={cn(
            'p-1.5 rounded-md',
            'bg-card dark:bg-muted',
            'border border-border',
            'text-muted-foreground hover:text-foreground',
            'transition-all duration-200',
            'text-xs font-medium flex items-center gap-1',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            'opacity-0 group-hover:opacity-100',
            copied && 'opacity-100'
          )}
          aria-label="Copy message"
          title="Copy"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" />
              <span className="sr-only">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span className="sr-only">Copy</span>
            </>
          )}
        </motion.button>

        {/* Delete button */}
        {onDelete && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleDelete}
            className={cn(
              'p-1.5 rounded-md',
              'bg-card dark:bg-muted',
              'border border-border',
              'text-destructive hover:text-destructive',
              'hover:bg-destructive/10',
              'transition-all duration-200',
              'text-xs font-medium flex items-center gap-1',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              'opacity-0 group-hover:opacity-100'
            )}
            aria-label="Delete message"
            title="Delete"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span className="sr-only">Delete</span>
          </motion.button>
        )}
      </motion.div>
    </AnimatePresence>
  );
}

export const MessageActions = memo(PureMessageActions);
