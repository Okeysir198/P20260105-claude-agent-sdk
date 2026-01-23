'use client';
import type { ChatMessage } from '@/types';
import { formatTime } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, XCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

interface ToolResultMessageProps {
  message: ChatMessage;
}

export function ToolResultMessage({ message }: ToolResultMessageProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="group flex gap-3 p-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-muted">
        {message.isError ? (
          <XCircle className="h-4 w-4 text-destructive" />
        ) : (
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-500" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <Card className="overflow-hidden">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start rounded-none border-b px-4 py-2 font-mono text-xs hover:bg-muted/50"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronDown className="mr-2 h-4 w-4" /> : <ChevronRight className="mr-2 h-4 w-4" />}
            {message.isError ? 'Error Output' : 'Tool Output'}
          </Button>
          {expanded && (
            <pre className="max-h-96 overflow-auto bg-muted p-4 text-xs">
              {message.content}
            </pre>
          )}
        </Card>
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}
