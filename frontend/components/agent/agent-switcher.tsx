'use client';
import { useAgents } from '@/hooks/use-agents';
import { useChatStore } from '@/lib/store/chat-store';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Bot, ChevronDown } from 'lucide-react';

export function AgentSwitcher() {
  const { data: agents, isLoading } = useAgents();
  const agentId = useChatStore((s) => s.agentId);
  const setAgentId = useChatStore((s) => s.setAgentId);

  const currentAgent = agents?.find((a) => a.agent_id === agentId);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="gap-1.5 h-7 px-2 min-w-[100px] sm:min-w-[200px] max-w-[120px] sm:max-w-none justify-start font-normal text-xs"
        >
          <Bot className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate flex-1 text-left sm:inline hidden">
            {currentAgent?.name || 'Agent'}
          </span>
          <span className="truncate flex-1 text-left sm:hidden max-w-[60px]">
            {currentAgent?.name ? currentAgent.name.split(' ')[0] : 'Agent'}
          </span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 ml-auto" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[280px]">
        <DropdownMenuLabel>Switch Agent</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {isLoading ? (
          <div className="px-2 py-4 text-center text-sm text-muted-foreground">
            Loading agents...
          </div>
        ) : (
          agents?.map((agent) => (
            <DropdownMenuItem
              key={agent.agent_id}
              onClick={() => setAgentId(agent.agent_id)}
              className="flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-2">
                <Bot className={cn(
                  "h-4 w-4 shrink-0",
                  agentId === agent.agent_id && "text-primary"
                )} />
                <span>{agent.name}</span>
              </div>
              {agentId === agent.agent_id && (
                <div className="h-2 w-2 rounded-full bg-primary" />
              )}
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
