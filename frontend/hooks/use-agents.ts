'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiRequest, getApiErrorMessage } from '@/lib/api-client';

/**
 * Agent information returned from the backend API.
 */
export interface Agent {
  agent_id: string;
  name: string;
  description: string;
  model: string;
  is_default: boolean;
}

interface UseAgentsResult {
  agents: Agent[];
  loading: boolean;
  error: string | null;
  defaultAgent: Agent | null;
  refresh: () => Promise<void>;
}

/**
 * Hook to fetch and manage the list of available agents.
 * Retrieves agents from GET /api/v1/config/agents endpoint.
 */
export function useAgents(): UseAgentsResult {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiRequest('/config/agents');

      if (!response.ok) {
        const errorMessage = await getApiErrorMessage(response, 'Failed to fetch agents');
        throw new Error(errorMessage);
      }

      const data = await response.json();
      const agentList: Agent[] = data.agents || [];
      setAgents(agentList);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch agents';
      setError(message);
      console.error('Error fetching agents:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  // Find the default agent
  const defaultAgent = agents.find(agent => agent.is_default) || agents[0] || null;

  return {
    agents,
    loading,
    error,
    defaultAgent,
    refresh: fetchAgents,
  };
}
