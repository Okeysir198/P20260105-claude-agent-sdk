'use client';
import type { ChatMessage } from '@/types';
import { formatTime } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Wrench, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

interface ToolUseMessageProps {
  message: ChatMessage;
}

export function ToolUseMessage({ message }: ToolUseMessageProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="group flex gap-3 p-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-primary/10">
        <Wrench className="h-4 w-4 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        {message.toolInput && (
          <Card className="overflow-hidden rounded-md shadow-none max-w-2xl">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start rounded-none border-b px-4 py-2 font-mono text-xs hover:bg-muted/50"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <ChevronDown className="mr-2 h-4 w-4" /> : <ChevronRight className="mr-2 h-4 w-4" />}
              {message.toolName} Tool Input
            </Button>
            {expanded && (
              <pre className="max-h-64 overflow-auto bg-muted p-4 text-xs">
                {JSON.stringify(message.toolInput, null, 2)}
              </pre>
            )}
          </Card>
        )}
        <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}
