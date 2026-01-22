'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
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
  favoriteAgents: Set<string>;
  toggleFavorite: (agentId: string) => void;
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

  // Load favorite agents from localStorage
  const favoriteAgents = useMemo(() => {
    try {
      const stored = localStorage.getItem('favorite_agents');
      if (stored) {
        const parsed = JSON.parse(stored) as string[];
        return new Set<string>(parsed);
      }
      return new Set<string>();
    } catch {
      return new Set<string>();
    }
  }, []);

  // Toggle favorite agent
  const toggleFavorite = useCallback((agentId: string) => {
    try {
      const stored = localStorage.getItem('favorite_agents');
      const favorites = stored ? JSON.parse(stored) : [];

      if (favorites.includes(agentId)) {
        const newFavorites = favorites.filter((id: string) => id !== agentId);
        localStorage.setItem('favorite_agents', JSON.stringify(newFavorites));
      } else {
        localStorage.setItem('favorite_agents', JSON.stringify([...favorites, agentId]));
      }

      // Force re-render by updating agents state
      setAgents(prev => [...prev]);
    } catch (error) {
      console.error('Failed to toggle favorite agent:', error);
    }
  }, []);

  // Find the default agent
  const defaultAgent = agents.find(agent => agent.is_default) || agents[0] || null;

  return {
    agents,
    loading,
    error,
    defaultAgent,
    favoriteAgents,
    toggleFavorite,
    refresh: fetchAgents,
  };
}
