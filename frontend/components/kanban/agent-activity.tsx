'use client';

import { useState, useMemo } from 'react';
import { useKanbanStore } from '@/lib/store/kanban-store';
import { getToolConfig, getToolColorStyles } from '@/lib/tool-config';
import { cn, formatTime } from '@/lib/utils';
import { createElement } from 'react';
import { ChevronDown, ChevronRight, Check, X, Loader2 } from 'lucide-react';
import type { AgentToolCall } from '@/lib/store/kanban-store';

function ToolCallStatus({ status }: { status: AgentToolCall['status'] }) {
  switch (status) {
    case 'completed':
      return <Check className="h-3 w-3 text-status-success shrink-0" />;
    case 'error':
      return <X className="h-3 w-3 text-status-error shrink-0" />;
    default:
      return <Loader2 className="h-3 w-3 text-status-info animate-spin shrink-0" />;
  }
}

function ToolCallRow({ call }: { call: AgentToolCall }) {
  const config = getToolConfig(call.toolName);
  const colorStyles = getToolColorStyles(call.toolName);

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 text-[10px] hover:bg-muted/30 rounded transition-colors">
      <div
        className="h-4 w-4 rounded flex items-center justify-center shrink-0"
        style={colorStyles.iconBg}
      >
        {createElement(config.icon, { className: 'h-2.5 w-2.5', style: colorStyles.iconText })}
      </div>
      <span className="font-medium shrink-0 w-12 truncate">{call.toolName}</span>
      <span className="text-muted-foreground truncate flex-1 min-w-0">{call.summary}</span>
      <ToolCallStatus status={call.status} />
      <span className="text-muted-foreground shrink-0 tabular-nums">
        {formatTime(call.timestamp)}
      </span>
    </div>
  );
}

interface AgentGroupProps {
  agentName: string;
  calls: AgentToolCall[];
  isSubagent: boolean;
}

function AgentGroup({ agentName, calls, isSubagent }: AgentGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasRunning = calls.some((c) => c.status === 'running');
  const displayName = isSubagent ? `${agentName} (subagent)` : 'Main Agent';

  return (
    <div className="mb-2">
      <button
        className="flex items-center gap-1.5 w-full text-left px-1 py-1 hover:bg-muted/50 rounded cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
        type="button"
      >
        {isExpanded
          ? <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
          : <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
        }
        <span className={cn(
          'text-[11px] font-semibold',
          hasRunning && 'animate-pulse'
        )}>
          {displayName}
        </span>
        <span className="text-[10px] text-muted-foreground">({calls.length})</span>
        {hasRunning && (
          <Loader2 className="h-3 w-3 text-status-info animate-spin ml-auto shrink-0" />
        )}
      </button>

      {isExpanded && (
        <div className="ml-1 border-l border-border pl-1 mt-0.5">
          {calls.map((call) => (
            <ToolCallRow key={call.id} call={call} />
          ))}
        </div>
      )}
    </div>
  );
}

export function AgentActivity() {
  const toolCalls = useKanbanStore((s) => s.toolCalls);
  const subagents = useKanbanStore((s) => s.subagents);

  const grouped = useMemo(() => {
    const groups = new Map<string, AgentToolCall[]>();

    // Ensure "main" is always first
    groups.set('main', []);

    for (const call of toolCalls) {
      const agent = call.agent;
      if (!groups.has(agent)) {
        groups.set(agent, []);
      }
      groups.get(agent)!.push(call);
    }

    return groups;
  }, [toolCalls]);

  const subagentTypes = new Set(subagents.map((s) => s.type));

  if (toolCalls.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-[11px] text-muted-foreground italic">
        No tool calls yet
      </div>
    );
  }

  return (
    <div className="pt-2 pb-4">
      {Array.from(grouped.entries()).map(([agent, calls]) => {
        if (calls.length === 0) return null;
        return (
          <AgentGroup
            key={agent}
            agentName={agent}
            calls={calls}
            isSubagent={subagentTypes.has(agent)}
          />
        );
      })}
    </div>
  );
}
