'use client';

import { useMemo } from 'react';
import { diffLines, Change } from 'diff';
import { cn } from '@/lib/utils';

interface DiffViewProps {
  oldContent: string;
  newContent: string;
  fileName?: string;
  maxLines?: number;
}

/**
 * Displays a unified diff view showing additions and deletions.
 */
export function DiffView({
  oldContent,
  newContent,
  fileName,
  maxLines = 30,
}: DiffViewProps) {
  const changes = useMemo(
    () => diffLines(oldContent, newContent),
    [oldContent, newContent]
  );

  // Count total lines for display
  const totalChanges = useMemo(() => {
    let added = 0;
    let removed = 0;
    changes.forEach((part) => {
      const lineCount = part.value.split('\n').filter(Boolean).length;
      if (part.added) added += lineCount;
      if (part.removed) removed += lineCount;
    });
    return { added, removed };
  }, [changes]);

  // Flatten changes into individual lines with metadata
  const diffLinesArray = useMemo(() => {
    const lines: Array<{ text: string; type: 'added' | 'removed' | 'unchanged' }> = [];

    changes.forEach((part) => {
      const partLines = part.value.split('\n');
      // Remove trailing empty string from split
      if (partLines[partLines.length - 1] === '') {
        partLines.pop();
      }

      partLines.forEach((line) => {
        lines.push({
          text: line,
          type: part.added ? 'added' : part.removed ? 'removed' : 'unchanged',
        });
      });
    });

    return lines;
  }, [changes]);

  const truncated = diffLinesArray.length > maxLines;
  const displayLines = truncated ? diffLinesArray.slice(0, maxLines) : diffLinesArray;

  return (
    <div className="font-mono text-[11px] sm:text-xs border rounded-md overflow-hidden border-border/50">
      {/* Header */}
      <div className="flex items-center justify-between bg-muted/50 px-2 sm:px-3 py-1.5 border-b border-border/50 flex-wrap gap-y-1">
        <div className="flex items-center gap-2">
          {fileName && (
            <span className="text-xs sm:text-[11px] text-muted-foreground font-medium">
              {fileName}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs sm:text-[10px]">
          <span className="text-green-600 dark:text-green-400">
            +{totalChanges.added}
          </span>
          <span className="text-red-600 dark:text-red-400">
            -{totalChanges.removed}
          </span>
        </div>
      </div>

      {/* Diff content */}
      <div className="overflow-auto max-h-48 sm:max-h-64 bg-background/50">
        {displayLines.map((line, index) => (
          <div
            key={index}
            className={cn(
              'px-2 sm:px-3 py-0.5 flex items-start gap-1.5 sm:gap-2 leading-relaxed',
              line.type === 'added' && 'bg-green-500/10',
              line.type === 'removed' && 'bg-red-500/10'
            )}
          >
            <span
              className={cn(
                'select-none w-4 shrink-0 text-center',
                line.type === 'added' && 'text-green-600 dark:text-green-400',
                line.type === 'removed' && 'text-red-600 dark:text-red-400',
                line.type === 'unchanged' && 'text-muted-foreground/50'
              )}
            >
              {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
            </span>
            <span
              className={cn(
                'flex-1 whitespace-pre-wrap break-all',
                line.type === 'added' && 'text-green-700 dark:text-green-300',
                line.type === 'removed' && 'text-red-700 dark:text-red-300 line-through opacity-80',
                line.type === 'unchanged' && 'text-foreground/80'
              )}
            >
              {line.text || '\u00A0'}
            </span>
          </div>
        ))}

        {truncated && (
          <div className="px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-[11px] text-muted-foreground italic border-t border-border/30 bg-muted/20">
            ... {diffLinesArray.length - maxLines} more lines
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Simple inline diff display for shorter content.
 */
export function InlineDiff({
  oldContent,
  newContent,
}: {
  oldContent: string;
  newContent: string;
}) {
  return (
    <div className="space-y-1.5">
      <div
        className="p-1.5 sm:p-2 rounded text-[11px] sm:text-xs font-mono whitespace-pre-wrap break-all border border-border/50"
        style={{
          backgroundColor: 'hsl(var(--destructive) / 0.08)',
        }}
      >
        <span className="text-red-600 dark:text-red-400 select-none mr-2">-</span>
        <span className="text-red-700 dark:text-red-300 line-through opacity-80">
          {oldContent.length > 200 ? oldContent.slice(0, 200) + '...' : oldContent}
        </span>
      </div>
      <div
        className="p-1.5 sm:p-2 rounded text-[11px] sm:text-xs font-mono whitespace-pre-wrap break-all border border-border/50"
        style={{
          backgroundColor: 'hsl(142 71% 45% / 0.08)',
        }}
      >
        <span className="text-green-600 dark:text-green-400 select-none mr-2">+</span>
        <span className="text-green-700 dark:text-green-300">
          {newContent.length > 200 ? newContent.slice(0, 200) + '...' : newContent}
        </span>
      </div>
    </div>
  );
}
