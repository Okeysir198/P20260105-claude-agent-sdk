const AGENT_COLORS: Record<string, string> = {
  main: 'bg-muted/80 text-muted-foreground border-border',
  explore: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
  Explore: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
};

const AGENT_TEXT_COLORS: Record<string, string> = {
  main: 'text-muted-foreground',
  explore: 'text-orange-600 dark:text-orange-400',
  Explore: 'text-orange-600 dark:text-orange-400',
};

export function getAgentColor(agent: string): string {
  if (AGENT_COLORS[agent]) return AGENT_COLORS[agent];
  if (agent.startsWith('test')) return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
  if (agent.includes('code') || agent.includes('lean')) return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
  return 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20';
}

export function getAgentTextColor(agent: string): string {
  if (AGENT_TEXT_COLORS[agent]) return AGENT_TEXT_COLORS[agent];
  if (agent.startsWith('test')) return 'text-purple-600 dark:text-purple-400';
  if (agent.includes('code') || agent.includes('lean')) return 'text-emerald-600 dark:text-emerald-400';
  return 'text-cyan-600 dark:text-cyan-400';
}
