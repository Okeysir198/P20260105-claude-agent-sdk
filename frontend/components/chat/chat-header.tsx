'use client';

import { Button } from '@/components/ui/button';
import { Trash2, RefreshCw, Hash, MessageSquare, Bot, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Agent } from '@/hooks/use-agents';

interface ChatHeaderProps {
  sessionId?: string | null;
  turnCount?: number;
  isStreaming?: boolean;
  onNewSession?: () => void;
  onClear?: () => void;
  className?: string;
  // Agent selection props
  agents?: Agent[];
  selectedAgentId?: string | null;
  onAgentChange?: (agentId: string) => void;
  agentsLoading?: boolean;
}

export function ChatHeader({
  sessionId,
  turnCount = 0,
  isStreaming = false,
  onNewSession,
  onClear,
  className,
  agents = [],
  selectedAgentId,
  onAgentChange,
  agentsLoading = false,
}: ChatHeaderProps) {
  // Format session ID for display (truncate if too long)
  const displaySessionId = sessionId
    ? sessionId.length > 12
      ? `${sessionId.slice(0, 8)}...`
      : sessionId
    : 'New Session';

  // Find the currently selected agent
  const selectedAgent = agents.find(agent => agent.agent_id === selectedAgentId);

  return (
    <header
      className={cn(
        'flex items-center justify-between px-4 py-3',
        'border-b border-[var(--claude-border)]',
        'bg-[var(--claude-background)]',
        className
      )}
    >
      {/* Left side: Agent selector and Session info */}
      <div className="flex items-center gap-4">
        {/* Agent Selector */}
        {agents.length > 0 && onAgentChange && (
          <div className="relative">
            <select
              value={selectedAgentId || ''}
              onChange={(e) => onAgentChange(e.target.value)}
              disabled={isStreaming || agentsLoading}
              className={cn(
                'appearance-none cursor-pointer',
                'pl-8 pr-8 py-1.5 rounded-lg',
                'text-sm font-medium',
                'bg-surface-secondary border border-border-primary',
                'text-text-primary',
                'hover:bg-surface-tertiary',
                'focus:outline-none focus:ring-2 focus:ring-claude-orange-500/50',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors duration-200'
              )}
              title={selectedAgent?.description || 'Select an agent'}
            >
              {agents.map((agent) => (
                <option key={agent.agent_id} value={agent.agent_id}>
                  {agent.name}
                </option>
              ))}
            </select>
            {/* Bot icon on the left */}
            <Bot className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-claude-orange-500 pointer-events-none" />
            {/* Chevron on the right */}
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary pointer-events-none" />
          </div>
        )}

        {/* Loading indicator for agents */}
        {agentsLoading && (
          <div className="flex items-center gap-2 text-sm text-text-tertiary">
            <div className="h-4 w-4 border-2 border-claude-orange-500 border-t-transparent rounded-full animate-spin" />
            <span>Loading agents...</span>
          </div>
        )}

        {/* Divider */}
        {agents.length > 0 && (
          <div className="h-5 w-px bg-border-primary" />
        )}

        {/* Session ID */}
        <div className="flex items-center gap-2 text-sm">
          <Hash className="h-4 w-4 text-[var(--claude-foreground-muted)]" />
          <span
            className="font-mono text-[var(--claude-foreground-muted)]"
            title={sessionId || 'No active session'}
          >
            {displaySessionId}
          </span>
        </div>

        {/* Turn count */}
        <div className="flex items-center gap-1.5 text-sm text-[var(--claude-foreground-muted)]">
          <MessageSquare className="h-4 w-4" />
          <span>{turnCount} {turnCount === 1 ? 'turn' : 'turns'}</span>
        </div>

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--claude-primary)] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--claude-primary)]" />
            </span>
            <span className="text-xs text-[var(--claude-primary)]">Streaming</span>
          </div>
        )}
      </div>

      {/* Right side: Actions */}
      <div className="flex items-center gap-2">
        {/* Clear conversation button */}
        {onClear && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            disabled={isStreaming}
            className="text-[var(--claude-foreground-muted)] hover:text-[var(--claude-foreground)]"
            title="Clear conversation"
          >
            <Trash2 className="h-4 w-4" />
            <span className="sr-only">Clear</span>
          </Button>
        )}

        {/* New session button */}
        {onNewSession && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onNewSession}
            disabled={isStreaming}
            className="text-[var(--claude-foreground-muted)] hover:text-[var(--claude-foreground)]"
            title="Start new session"
          >
            <RefreshCw className="h-4 w-4" />
            <span className="sr-only">New Session</span>
          </Button>
        )}
      </div>
    </header>
  );
}
