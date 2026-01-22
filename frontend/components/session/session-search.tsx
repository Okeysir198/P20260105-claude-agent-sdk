'use client';

import { useState, useCallback, useMemo } from 'react';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface SessionSearchProps {
  sessions: Array<{ id: string; preview?: string; title?: string }>;
  onFilteredSessionsChange: (sessions: string[]) => void;
  className?: string;
}

/**
 * Simple fuzzy match implementation (no external dependencies)
 * Matches if all characters in query appear in target in order
 */
function fuzzyMatch(query: string, target: string): boolean {
  if (!query) return true;

  const q = query.toLowerCase();
  const t = target.toLowerCase();

  let queryIndex = 0;
  for (let i = 0; i < t.length && queryIndex < q.length; i++) {
    if (t[i] === q[queryIndex]) {
      queryIndex++;
    }
  }

  return queryIndex === q.length;
}

export function SessionSearch({
  sessions,
  onFilteredSessionsChange,
  className,
}: SessionSearchProps) {
  const [query, setQuery] = useState('');

  const filteredIds = useMemo(() => {
    if (!query) return sessions.map(s => s.id);

    return sessions
      .filter(session => {
        const searchableText = [
          session.title,
          session.preview,
          session.id,
        ]
          .filter(Boolean)
          .join(' ');

        return fuzzyMatch(query, searchableText);
      })
      .map(s => s.id);
  }, [sessions, query]);

  const handleClear = useCallback(() => {
    setQuery('');
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  }, []);

  // Notify parent of filtered results
  useMemo(() => {
    onFilteredSessionsChange(filteredIds);
  }, [filteredIds, onFilteredSessionsChange]);

  return (
    <div className={cn('relative', className)}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary pointer-events-none" />
      <Input
        type="text"
        value={query}
        onChange={handleChange}
        placeholder="Search sessions..."
        className={cn(
          'pl-9 pr-10',
          'h-9 text-sm',
          'bg-surface-tertiary border-border-primary',
          'placeholder:text-text-tertiary',
          'focus:bg-surface-secondary'
        )}
      />
      {query && (
        <Button
          variant="ghost"
          size="icon"
          onClick={handleClear}
          className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 text-text-tertiary hover:text-text-primary"
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}
