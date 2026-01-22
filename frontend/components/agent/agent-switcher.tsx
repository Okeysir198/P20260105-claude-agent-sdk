'use client';

import { useState, useCallback, useMemo } from 'react';
import { Bot, ChevronDown, Star, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

interface Agent {
  agent_id: string;
  name: string;
  description?: string;
  is_default?: boolean;
}

interface AgentSwitcherProps {
  agents: Agent[];
  selectedAgentId: string | null;
  onAgentChange: (agentId: string) => void;
  disabled?: boolean;
  className?: string;
  favoriteAgents?: Set<string>;
  onToggleFavorite?: (agentId: string) => void;
}

export function AgentSwitcher({
  agents,
  selectedAgentId,
  onAgentChange,
  disabled = false,
  className,
  favoriteAgents = new Set(),
  onToggleFavorite,
}: AgentSwitcherProps) {
  const [open, setOpen] = useState(false);

  const selectedAgent = useMemo(
    () => agents.find((a) => a.agent_id === selectedAgentId),
    [agents, selectedAgentId]
  );

  const favorites = useMemo(
    () => agents.filter((a) => favoriteAgents.has(a.agent_id)),
    [agents, favoriteAgents]
  );

  const regularAgents = useMemo(
    () => agents.filter((a) => !favoriteAgents.has(a.agent_id)),
    [agents, favoriteAgents]
  );

  const handleSelect = useCallback(
    (agentId: string) => {
      onAgentChange(agentId);
      setOpen(false);
    },
    [onAgentChange]
  );

  const handleToggleFavorite = useCallback(
    (e: React.MouseEvent, agentId: string) => {
      e.stopPropagation();
      onToggleFavorite?.(agentId);
    },
    [onToggleFavorite]
  );

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'justify-between gap-2',
            'bg-surface-secondary border-border-primary',
            'hover:bg-surface-tertiary',
            'transition-colors duration-200',
            disabled && 'opacity-50 cursor-not-allowed',
            className
          )}
          disabled={disabled}
        >
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-claude-orange-500" />
            <span className="text-sm font-medium">
              {selectedAgent?.name || 'Select Agent'}
            </span>
          </div>
          <ChevronDown className="h-4 w-4 text-text-tertiary" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-56">
        {/* Favorites section */}
        {favorites.length > 0 && (
          <>
            <div className="px-2 py-1.5 text-xs font-medium text-text-tertiary uppercase">
              Favorites
            </div>
            {favorites.map((agent) => (
              <DropdownMenuItem
                key={agent.agent_id}
                onClick={() => handleSelect(agent.agent_id)}
                className="cursor-pointer"
              >
                <div className="flex-1 flex items-center gap-2">
                  <Bot className="h-4 w-4 text-claude-orange-500" />
                  <span className="flex-1">{agent.name}</span>
                  {agent.agent_id === selectedAgentId && (
                    <Check className="h-4 w-4 text-text-primary" />
                  )}
                </div>
                {onToggleFavorite && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 ml-2 text-claude-orange-600 hover:text-claude-orange-700"
                    onClick={(e) => handleToggleFavorite(e, agent.agent_id)}
                  >
                    <Star className="h-3.5 w-3.5 fill-current" />
                  </Button>
                )}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
          </>
        )}

        {/* All agents */}
        <div className="px-2 py-1.5 text-xs font-medium text-text-tertiary uppercase">
          All Agents
        </div>
        {regularAgents.map((agent) => (
          <DropdownMenuItem
            key={agent.agent_id}
            onClick={() => handleSelect(agent.agent_id)}
            className="cursor-pointer"
          >
            <div className="flex-1 flex items-center gap-2">
              <Bot className="h-4 w-4 text-text-tertiary" />
              <div className="flex-1">
                <div className="text-sm">{agent.name}</div>
                {agent.description && (
                  <div className="text-xs text-text-tertiary truncate">
                    {agent.description}
                  </div>
                )}
              </div>
              {agent.agent_id === selectedAgentId && (
                <Check className="h-4 w-4 text-text-primary" />
              )}
            </div>
            {onToggleFavorite && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 ml-2 text-text-tertiary hover:text-claude-orange-600"
                onClick={(e) => handleToggleFavorite(e, agent.agent_id)}
              >
                <Star className="h-3.5 w-3.5" />
              </Button>
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
