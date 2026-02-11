'use client';

import { useState, useMemo } from 'react';
import { useKanbanStore } from '@/lib/store/kanban-store';
import { config } from '@/lib/config';
import { getToolConfig, getToolColorStyles } from '@/lib/tool-config';
import { cn, formatTime } from '@/lib/utils';
import { createElement } from 'react';
import { ChevronDown, ChevronRight, Check, X, Loader2, MessageSquare, Bot } from 'lucide-react';
import { getAgentTextColor } from './agent-colors';
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

function ToolCallRow({ call, onSelect, isNarrow, showAgent }: { call: AgentToolCall; onSelect?: (call: AgentToolCall) => void; isNarrow: boolean; showAgent?: boolean }) {
  const isText = call.toolName === '__text__';
  const toolConfig = isText ? null : getToolConfig(call.toolName);
  const colorStyles = isText ? null : getToolColorStyles(call.toolName);

  return (
    <button
      type="button"
      className="flex items-center gap-1.5 px-2 py-1 text-[10px] hover:bg-muted/30 rounded transition-colors w-full text-left cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      onClick={() => onSelect?.(call)}
    >
      {showAgent && (
        <span
          className={cn('shrink-0', getAgentTextColor(call.agent))}
          title={call.agent === 'main' ? 'Main Agent' : call.agent}
        >
          <Bot className="h-3 w-3" />
        </span>
      )}
      {isText ? (
        <div className="h-4 w-4 rounded flex items-center justify-center shrink-0 bg-primary/10">
          {createElement(MessageSquare, { className: 'h-2.5 w-2.5 text-primary' })}
        </div>
      ) : (
        <div
          className="h-4 w-4 rounded flex items-center justify-center shrink-0"
          style={colorStyles!.iconBg}
        >
          {createElement(toolConfig!.icon, { className: 'h-2.5 w-2.5', style: colorStyles!.iconText })}
        </div>
      )}
      <span className={cn("font-medium shrink-0 truncate", isNarrow ? "w-12" : "w-16")}>
        {isText ? 'Text' : call.toolName}
      </span>
      <span className="text-muted-foreground truncate flex-1 min-w-0">{call.summary}</span>
      <ToolCallStatus status={call.status} />
      {!isNarrow && (
        <span className="text-muted-foreground shrink-0 tabular-nums">
          {formatTime(call.timestamp)}
        </span>
      )}
    </button>
  );
}

interface AgentGroupProps {
  agentName: string;
  calls: AgentToolCall[];
  isSubagent: boolean;
  isNarrow: boolean;
  subtitle?: string;
  onSelectToolCall?: (call: AgentToolCall) => void;
}

function AgentGroup({ agentName, calls, isSubagent, isNarrow, subtitle, onSelectToolCall }: AgentGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasRunning = calls.some((c) => c.status === 'running');
  const displayName = isSubagent ? `Sub-Agent: ${agentName}` : 'Main Agent';

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
        <Bot className={cn('h-3.5 w-3.5 shrink-0', getAgentTextColor(agentName))} />
        <span className={cn(
          'text-[11px] font-semibold',
          hasRunning && 'animate-pulse'
        )}>
          {displayName}
        </span>
        <span className="text-[10px] text-muted-foreground">({calls.length})</span>
        {subtitle && (
          <span className="text-[9px] text-muted-foreground truncate flex-1 min-w-0" title={subtitle}>
            {subtitle}
          </span>
        )}
        {hasRunning && (
          <Loader2 className="h-3 w-3 text-status-info animate-spin ml-auto shrink-0" />
        )}
      </button>

      {isExpanded && (
        <div className="ml-1 border-l border-border pl-1 mt-0.5">
          {calls.map((call) => (
            <ToolCallRow key={call.id} call={call} onSelect={onSelectToolCall} isNarrow={isNarrow} />
          ))}
        </div>
      )}
    </div>
  );
}

export type ActivityViewMode = 'grouped' | 'timeline';

interface AgentActivityProps {
  panelWidth?: number;
  viewMode?: ActivityViewMode;
  onSelectToolCall?: (call: AgentToolCall) => void;
}

interface GroupEntry {
  key: string;
  name: string;
  calls: AgentToolCall[];
  isSubagent: boolean;
  subtitle?: string;
}

export function AgentActivity({ panelWidth, viewMode = 'grouped', onSelectToolCall }: AgentActivityProps) {
  const toolCalls = useKanbanStore((s) => s.toolCalls);
  const subagents = useKanbanStore((s) => s.subagents);
  const isNarrow = (panelWidth ?? 320) < config.kanban.breakpoints.narrow;

  const groups = useMemo(() => {
    const result: GroupEntry[] = [];
    const mainCalls: AgentToolCall[] = [];
    const instanceMap = new Map<string, AgentToolCall[]>();
    const instanceOrder: string[] = [];

    for (const call of toolCalls) {
      if (call.agent === 'main') {
        mainCalls.push(call);
      } else if (call.parentToolUseId) {
        if (!instanceMap.has(call.parentToolUseId)) {
          instanceMap.set(call.parentToolUseId, []);
          instanceOrder.push(call.parentToolUseId);
        }
        instanceMap.get(call.parentToolUseId)!.push(call);
      } else {
        mainCalls.push(call);
      }
    }

    if (mainCalls.length > 0) {
      result.push({ key: 'main', name: 'main', calls: mainCalls, isSubagent: false });
    }

    for (const taskToolUseId of instanceOrder) {
      const calls = instanceMap.get(taskToolUseId)!;
      const subagent = subagents.find(s => s.taskToolUseId === taskToolUseId);
      const name = subagent?.type || calls[0]?.agent || 'subagent';
      const subtitle = subagent?.description || undefined;
      result.push({ key: taskToolUseId, name, calls, isSubagent: true, subtitle });
    }

    return result;
  }, [toolCalls, subagents]);

  const timelineCalls = useMemo(() => {
    return [...toolCalls].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [toolCalls]);

  if (toolCalls.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-[11px] text-muted-foreground italic">
        No tool calls yet
      </div>
    );
  }

  return (
    <div className="pt-2 pb-4">
      {viewMode === 'grouped' ? (
        groups.map((group) => (
          <AgentGroup
            key={group.key}
            agentName={group.name}
            calls={group.calls}
            isSubagent={group.isSubagent}
            isNarrow={isNarrow}
            subtitle={group.subtitle}
            onSelectToolCall={onSelectToolCall}
          />
        ))
      ) : (
        <div className="space-y-0">
          {timelineCalls.map((call) => (
            <ToolCallRow key={call.id} call={call} onSelect={onSelectToolCall} isNarrow={isNarrow} showAgent />
          ))}
        </div>
      )}
    </div>
  );
}
