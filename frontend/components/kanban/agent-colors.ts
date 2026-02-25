const AGENT_COLORS: Record<string, string> = {
  main: 'bg-muted/80 text-muted-foreground border-border',
  explore: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
};

const AGENT_TEXT_COLORS: Record<string, string> = {
  main: 'text-muted-foreground',
  explore: 'text-orange-600 dark:text-orange-400',
};

const DYNAMIC_COLORS = [
  { bg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20', text: 'text-blue-600 dark:text-blue-400' },
  { bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20', text: 'text-amber-600 dark:text-amber-400' },
  { bg: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20', text: 'text-rose-600 dark:text-rose-400' },
  { bg: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20', text: 'text-indigo-600 dark:text-indigo-400' },
  { bg: 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/20', text: 'text-teal-600 dark:text-teal-400' },
  { bg: 'bg-pink-500/10 text-pink-600 dark:text-pink-400 border-pink-500/20', text: 'text-pink-600 dark:text-pink-400' },
];

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function getAgentColor(agent: string): string {
  const key = agent.toLowerCase();
  if (AGENT_COLORS[key]) return AGENT_COLORS[key];
  if (key.startsWith('test')) return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
  if (key.includes('code') || key.includes('lean')) return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
  return DYNAMIC_COLORS[hashString(key) % DYNAMIC_COLORS.length].bg;
}

export function getAgentTextColor(agent: string): string {
  const key = agent.toLowerCase();
  if (AGENT_TEXT_COLORS[key]) return AGENT_TEXT_COLORS[key];
  if (key.startsWith('test')) return 'text-purple-600 dark:text-purple-400';
  if (key.includes('code') || key.includes('lean')) return 'text-emerald-600 dark:text-emerald-400';
  return DYNAMIC_COLORS[hashString(key) % DYNAMIC_COLORS.length].text;
}
