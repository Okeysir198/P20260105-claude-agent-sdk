'use client';
import { useAgents } from '@/hooks/use-agents';
import { useChatStore } from '@/lib/store/chat-store';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Bot, Sparkles } from 'lucide-react';

export function AgentGrid() {
  const { data: agents, isLoading, error } = useAgents();
  const setAgentId = useChatStore((s) => s.setAgentId);

  if (isLoading) {
    return (
      <div className="flex-1 overflow-auto">
        <div className="container mx-auto max-w-4xl p-8">
          <div className="mb-8 text-center">
            <Skeleton className="mx-auto h-16 w-16 rounded-full" />
            <Skeleton className="mx-auto mt-4 h-8 w-48" />
            <Skeleton className="mx-auto mt-2 h-4 w-96" />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <Card key={i} className="p-6">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="mt-4 h-4 w-full" />
                <Skeleton className="mt-2 h-4 w-3/4" />
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-destructive">Failed to load agents. Please try again.</p>
        </div>
      </div>
    );
  }

  const defaultAgent = agents?.find((a) => a.is_default);
  const otherAgents = agents?.filter((a) => !a.is_default) || [];

  return (
    <ScrollArea className="flex-1">
      <div className="container mx-auto max-w-4xl p-8">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Sparkles className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold">Welcome to Claude Agent SDK</h1>
          <p className="mt-2 text-muted-foreground">Select an agent to start your conversation</p>
        </div>

        <div className="space-y-4">
          {defaultAgent && (
            <Card
              className="cursor-pointer border-primary/50 bg-primary/5 transition-colors hover:bg-primary/10"
              onClick={() => setAgentId(defaultAgent.agent_id)}
            >
              <div className="flex items-start gap-4 p-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary">
                  <Bot className="h-6 w-6 text-primary-foreground" />
                </div>
                <div className="flex-1">
                  <div className="mb-2 flex items-center gap-2">
                    <h3 className="text-lg font-semibold">{defaultAgent.name}</h3>
                    <Badge variant="default" className="text-xs">
                      Default
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{defaultAgent.description}</p>
                  <p className="mt-2 text-xs text-muted-foreground">Model: {defaultAgent.model}</p>
                </div>
              </div>
            </Card>
          )}

          {otherAgents.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {otherAgents.map((agent) => (
                <Card
                  key={agent.agent_id}
                  className="cursor-pointer transition-colors hover:bg-muted/50"
                  onClick={() => setAgentId(agent.agent_id)}
                >
                  <div className="flex items-start gap-4 p-6">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                      <Bot className="h-6 w-6" />
                    </div>
                    <div className="flex-1">
                      <h3 className="mb-2 text-lg font-semibold">{agent.name}</h3>
                      <p className="text-sm text-muted-foreground">{agent.description}</p>
                      <p className="mt-2 text-xs text-muted-foreground">Model: {agent.model}</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </ScrollArea>
  );
}
