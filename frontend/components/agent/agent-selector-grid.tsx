'use client';

import { memo, useState, useCallback, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import {
  Bot,
  FileText,
  Search,
  Shield,
  Lock,
  Sparkles,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Agent } from '@/hooks/use-agents';

/**
 * Agent icon mapping based on agent name or ID.
 */
function getAgentIcon(agent: Agent): React.ReactNode {
  const { name, agent_id } = agent;
  const lowerName = name.toLowerCase();
  const lowerId = agent_id.toLowerCase();

  if (lowerName.includes('general') || lowerId.includes('general')) {
    return <Bot className="size-6" />;
  }
  if (lowerName.includes('review') || lowerId.includes('review')) {
    return <Shield className="size-6" />;
  }
  if (lowerName.includes('doc') || lowerId.includes('doc')) {
    return <FileText className="size-6" />;
  }
  if (lowerName.includes('research') || lowerId.includes('research')) {
    return <Search className="size-6" />;
  }
  if (lowerName.includes('sandbox') || lowerId.includes('sandbox')) {
    return <Lock className="size-6" />;
  }

  // Default icon
  return <Sparkles className="size-6" />;
}

/**
 * Individual agent card component.
 */
interface AgentCardProps {
  agent: Agent;
  isSelected: boolean;
  onSelect: (agentId: string) => void;
  index: number;
}

const AgentCard = memo(function AgentCard({
  agent,
  isSelected,
  onSelect,
  index,
}: AgentCardProps) {
  const handleClick = useCallback(() => {
    onSelect(agent.agent_id);
  }, [agent.agent_id, onSelect]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onSelect(agent.agent_id);
      }
    },
    [agent.agent_id, onSelect]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className={cn(
        'group relative touch-manipulation rounded-xl border p-4',
        'transition-all duration-200 cursor-pointer',
        'hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5',
        'active:scale-[0.98]',
        isSelected
          ? 'border-primary bg-primary/5 shadow-lg shadow-primary/10'
          : 'border-border bg-card hover:bg-accent/30'
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      aria-label={`Select ${agent.name}`}
    >
      <div className="flex items-start gap-4">
        {/* Icon container with hover effect */}
        <div
          className={cn(
            'flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center transition-all duration-200',
            isSelected
          ? 'bg-primary/20 text-primary'
          : 'bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary'
          )}
        >
          {getAgentIcon(agent)}
        </div>

        {/* Agent info */}
        <div className="flex-1 min-w-0">
          <h3
            className={cn(
              'font-medium transition-colors',
              isSelected
              ? 'text-primary'
              : 'text-card-foreground group-hover:text-primary'
            )}
          >
            {agent.name}
          </h3>
          <p
            className={cn(
              'mt-1 text-sm line-clamp-2 leading-relaxed',
              isSelected ? 'text-primary/80' : 'text-muted-foreground'
            )}
          >
            {agent.description}
          </p>

          {/* Model badge */}
          <div className="mt-2 flex items-center gap-2">
            <span
              className={cn(
                'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium',
                isSelected
                ? 'bg-primary/20 text-primary'
                : 'bg-muted text-muted-foreground'
              )}
            >
              {agent.model}
            </span>
            {agent.is_default && (
              <span
                className={cn(
                  'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium',
                  'bg-accent/20 text-accent-foreground'
                )}
              >
                Default
              </span>
            )}
          </div>
        </div>

        {/* Selection indicator */}
        <ChevronRight
          className={cn(
            'flex-shrink-0 size-5 transition-all duration-200',
            isSelected
            ? 'text-primary translate-x-0.5'
            : 'text-muted-foreground/50 group-hover:text-primary group-hover:translate-x-0.5'
          )}
        />
      </div>

      {/* Selection ring (when selected) */}
      {isSelected && (
        <motion.div
          layoutId="selectedRing"
          className="absolute inset-0 rounded-xl border-2 border-primary pointer-events-none"
          transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
        />
      )}
    </motion.div>
  );
});

/**
 * Props for the agent selector grid component.
 */
export interface AgentSelectorGridProps {
  /** List of available agents */
  agents: Agent[];
  /** Currently selected agent ID */
  selectedAgentId?: string | null;
  /** Callback when an agent is selected */
  onSelectAgent: (agentId: string) => void;
  /** Loading state */
  loading?: boolean;
  /** Optional error message */
  error?: string | null;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Agent selector grid component with responsive layout and keyboard navigation.
 *
 * Features:
 * - Responsive grid (2 cols mobile, 3 tablet, 4 desktop)
 * - Hover effects with lift animation
 * - Selection indicator with animated ring
 * - Keyboard navigation (arrow keys + Enter)
 * - ARIA labels for accessibility
 */
export const AgentSelectorGrid = memo(function AgentSelectorGrid({
  agents,
  selectedAgentId,
  onSelectAgent,
  loading = false,
  error = null,
  className,
}: AgentSelectorGridProps) {
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (agents.length === 0) return;

      switch (e.key) {
        case 'ArrowDown':
        case 'ArrowRight':
          e.preventDefault();
          setFocusedIndex((prev) => (prev + 1) % agents.length);
          break;
        case 'ArrowUp':
        case 'ArrowLeft':
          e.preventDefault();
          setFocusedIndex((prev) => (prev - 1 + agents.length) % agents.length);
          break;
        case 'Enter':
          e.preventDefault();
          if (focusedIndex >= 0 && focusedIndex < agents.length) {
            const agent = agents[focusedIndex];
            if (agent) {
              onSelectAgent(agent.agent_id);
            }
          }
          break;
        case 'Home':
          e.preventDefault();
          setFocusedIndex(0);
          break;
        case 'End':
          e.preventDefault();
          setFocusedIndex(agents.length - 1);
          break;
      }
    },
    [agents, focusedIndex, onSelectAgent]
  );

  // Loading state
  if (loading) {
    return (
      <div className={cn('flex flex-col items-center justify-center gap-4 p-8', className)}>
        <div className="animate-pulse space-y-4 w-full max-w-2xl">
          <div className="h-8 bg-muted rounded w-48 mx-auto" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-muted rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn('flex flex-col items-center justify-center gap-4 p-8', className)}>
        <div className="text-center">
          <h2 className="text-xl font-semibold text-card-foreground mb-2">
            Failed to load agents
          </h2>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (agents.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center gap-4 p-8', className)}>
        <div className="text-center">
          <h2 className="text-xl font-semibold text-card-foreground mb-2">
            No agents available
          </h2>
          <p className="text-sm text-muted-foreground">
            Please check your configuration or contact your administrator.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn('flex flex-col gap-6 p-4 sm:gap-8 sm:p-8', className)}
      onKeyDown={handleKeyDown}
      role="listbox"
      aria-label="Select an agent"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center"
      >
        <h1 className="text-2xl font-semibold tracking-tight text-card-foreground sm:text-3xl">
          Choose an Agent
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Select an AI assistant to help you with your tasks
        </p>
      </motion.div>

      {/* Agent grid - responsive layout */}
      <div className="mx-auto w-full max-w-5xl">
        <div className="grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {agents.map((agent, index) => (
            <AgentCard
              key={agent.agent_id}
              agent={agent}
              isSelected={selectedAgentId === agent.agent_id}
              onSelect={onSelectAgent}
              index={index}
            />
          ))}
        </div>
      </div>

      {/* Keyboard navigation hint */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="text-center text-xs text-muted-foreground"
      >
        Use arrow keys to navigate, Enter to select
      </motion.p>
    </div>
  );
});
