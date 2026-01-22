'use client';

import { useState, useCallback } from 'react';
import { Download, FileText, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { SessionInfo } from '@/types/sessions';

interface SessionExportProps {
  session: SessionInfo;
  messages?: Array<{ role: string; content: string }>;
  className?: string;
}

export function SessionExport({ session, messages = [], className }: SessionExportProps) {
  const [isExporting, setIsExporting] = useState(false);

  const exportAsMarkdown = useCallback(() => {
    setIsExporting(true);

    try {
      const lines: string[] = [];

      // Header
      lines.push(`# ${session.title || 'Conversation'}`);
      lines.push('');
      lines.push(`**Session ID:** \`${session.id}\``);
      lines.push(`**Created:** ${new Date(session.created_at).toLocaleString()}`);
      lines.push(`**Turns:** ${session.turn_count}`);
      if (session.agent_id) {
        lines.push(`**Agent:** ${session.agent_id}`);
      }
      lines.push('');
      lines.push('---');
      lines.push('');

      // Messages
      for (const msg of messages) {
        const role = msg.role === 'assistant' ? 'Claude' : 'User';
        lines.push(`### ${role}`);
        lines.push('');
        lines.push(msg.content);
        lines.push('');
        lines.push('---');
        lines.push('');
      }

      const content = lines.join('\n');
      const blob = new Blob([content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session-${session.id.slice(0, 8)}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  }, [session, messages]);

  const exportAsJSON = useCallback(() => {
    setIsExporting(true);

    try {
      const data = {
        session: {
          id: session.id,
          title: session.title,
          created_at: session.created_at,
          last_activity: session.last_activity,
          turn_count: session.turn_count,
          agent_id: session.agent_id,
          tags: session.tags,
        },
        messages,
      };

      const content = JSON.stringify(data, null, 2);
      const blob = new Blob([content], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session-${session.id.slice(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  }, [session, messages]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={className}
          disabled={isExporting}
          aria-label="Export session"
        >
          <Download className="h-3.5 w-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={exportAsMarkdown} disabled={isExporting}>
          <FileText className="h-4 w-4 mr-2" />
          Export as Markdown
        </DropdownMenuItem>
        <DropdownMenuItem onClick={exportAsJSON} disabled={isExporting}>
          <Database className="h-4 w-4 mr-2" />
          Export as JSON
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
