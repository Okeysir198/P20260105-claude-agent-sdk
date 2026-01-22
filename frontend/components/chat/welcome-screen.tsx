'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { AgentSelectorGrid } from '@/components/agent';
import type { Agent } from '@/hooks/use-agents';

/**
 * Claude logo SVG component.
 */
function ClaudeLogo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 80 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="40"
        cy="40"
        r="36"
        className="fill-primary/20 dark:fill-primary/10"
      />
      <path
        d="M40 16C26.745 16 16 26.745 16 40C16 53.255 26.745 64 40 64C53.255 64 64 53.255 64 40C64 26.745 53.255 16 40 16Z"
        className="fill-primary"
        fillOpacity="0.2"
      />
      <path
        d="M28 40C28 33.373 33.373 28 40 28C46.627 28 52 33.373 52 40C52 46.627 46.627 52 40 52"
        className="stroke-primary"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <circle
        cx="40"
        cy="40"
        r="6"
        className="fill-primary"
      />
    </svg>
  );
}

interface WelcomeScreenProps {
  className?: string;
  /** Agent selection props */
  agents?: Agent[];
  selectedAgentId?: string | null;
  onAgentSelect?: (agentId: string) => void;
  agentsLoading?: boolean;
}

export const WelcomeScreen = memo(function WelcomeScreen({
  className,
  agents = [],
  selectedAgentId,
  onAgentSelect,
  agentsLoading = false,
}: WelcomeScreenProps) {
  // Show agent selector if agents are available
  const showAgentSelector = agents.length > 0;

  return (
    <div className={cn('flex-1 flex flex-col items-center justify-center px-4 overflow-y-auto', className)}>
      {showAgentSelector ? (
        <>
          {/* Logo animation */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mb-6"
          >
            <ClaudeLogo className="w-16 h-16" />
          </motion.div>

          {/* Agent selector grid */}
          <AgentSelectorGrid
            agents={agents}
            selectedAgentId={selectedAgentId}
            onSelectAgent={onAgentSelect || (() => {})}
            loading={agentsLoading}
            className="w-full"
          />
        </>
      ) : (
        /* Original welcome screen (shown when no agents) */
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="flex flex-col items-center text-center max-w-md"
        >
          {/* Logo */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <ClaudeLogo className="w-20 h-20 mb-6" />
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-2xl font-serif text-foreground mb-2"
          >
            Hello, I&apos;m Claude
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="text-muted-foreground text-base mb-8 leading-relaxed"
          >
            I&apos;m an AI assistant created by Anthropic. I can help you with analysis, coding, writing, and more.
          </motion.p>

          {/* Suggestion chips */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="flex flex-wrap gap-2 justify-center"
          >
            {[
              'Explain a concept',
              'Help with code',
              'Write content',
              'Analyze data',
            ].map((suggestion) => (
              <span
                key={suggestion}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-full',
                  'bg-secondary border border-border',
                  'text-muted-foreground',
                  'transition-colors hover:bg-muted hover:text-foreground cursor-default'
                )}
              >
                {suggestion}
              </span>
            ))}
          </motion.div>
        </motion.div>
      )}

      {/* Footer - only show when not in agent selector mode */}
      {!showAgentSelector && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="absolute bottom-24 text-xs text-muted-foreground"
        >
          Type a message below to start the conversation
        </motion.p>
      )}
    </div>
  );
});
