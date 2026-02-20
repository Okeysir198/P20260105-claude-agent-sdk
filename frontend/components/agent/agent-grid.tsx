'use client';
import { useState } from 'react';
import { useAgents } from '@/hooks/use-agents';
import { useChatStore } from '@/lib/store/chat-store';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Bot, Sparkles, Send } from 'lucide-react';

export function AgentGrid() {
  const { data: agents, isLoading, error } = useAgents();
  const setAgentId = useChatStore((s) => s.setAgentId);
  const setPendingMessage = useChatStore((s) => s.setPendingMessage);
  const [message, setMessage] = useState('');

  const handleSendMessage = () => {
    if (!message.trim()) return;

    // Find default agent or first available agent
    const defaultAgent = agents?.find((a) => a.is_default) || agents?.[0];
    if (defaultAgent) {
      setPendingMessage(message.trim());
      setAgentId(defaultAgent.agent_id);
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

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

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <div className="container mx-auto max-w-4xl p-8">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Sparkles className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-3xl font-bold">Welcome to Claude Agent SDK</h1>
            <p className="mt-2 text-muted-foreground">Select an agent or start typing to begin</p>
          </div>

        <div className="grid gap-4 md:grid-cols-2">
          {agents?.map((agent) => {
            const isDefault = agent.is_default;
            return (
              <Card
                key={agent.agent_id}
                className={
                  isDefault
                    ? 'cursor-pointer border-primary/50 bg-primary/5 transition-colors hover:bg-primary/10'
                    : 'cursor-pointer transition-colors hover:bg-muted/50'
                }
                onClick={() => setAgentId(agent.agent_id)}
              >
                <div className="flex items-start gap-4 p-6">
                  <div
                    className={`flex h-12 w-12 items-center justify-center rounded-lg ${
                      isDefault ? 'bg-primary' : 'bg-muted'
                    }`}
                  >
                    <Bot className={`h-6 w-6 ${isDefault ? 'text-primary-foreground' : ''}`} />
                  </div>
                  <div className="flex-1">
                    <div className="mb-2 flex items-center gap-2">
                      <h3 className="font-semibold">{agent.name}</h3>
                      {isDefault && (
                        <Badge variant="default" className="text-xs">
                          Default
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">{agent.description}</p>
                    <p className="mt-2 text-xs text-muted-foreground">Model: {agent.model}</p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </ScrollArea>

    {/* Chat input */}
    <div className="bg-background px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-background p-2 shadow-sm">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message Claude..."
            className="chat-textarea flex-1 min-h-[60px] max-h-[200px] resize-none bg-transparent px-3 py-2 text-base md:text-sm placeholder:text-muted-foreground"
            style={{ outline: 'none', border: 'none', boxShadow: 'none' }}
            disabled={isLoading || !agents?.length}
          />
          <Button
            onClick={handleSendMessage}
            disabled={!message.trim() || isLoading || !agents?.length}
            size="icon"
            className="h-10 w-10 shrink-0 rounded-xl bg-primary text-white hover:bg-primary-hover disabled:opacity-50"
          >
            <Send className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </div>
  </div>
  );
}
