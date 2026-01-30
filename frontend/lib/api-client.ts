import { API_URL } from './constants';
import type {
  AgentInfo,
  SessionInfo,
  SessionResponse,
  SessionHistoryResponse,
  CreateSessionRequest,
  ResumeSessionRequest,
  SearchResponse
} from '@/types';

class ApiClient {
  private async fetchWithErrorHandling(url: string, options?: RequestInit): Promise<Response> {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || error.detail || 'Request failed');
    }

    return response;
  }

  async getAgents(): Promise<AgentInfo[]> {
    const res = await this.fetchWithErrorHandling(`${API_URL}/config/agents`);
    const data = await res.json();
    return data.agents;
  }

  async getSessions(): Promise<SessionInfo[]> {
    const res = await this.fetchWithErrorHandling(`${API_URL}/sessions`);
    return res.json();
  }

  async createSession(agentId?: string): Promise<SessionResponse> {
    const body: CreateSessionRequest = agentId ? { agent_id: agentId } : {};
    const res = await this.fetchWithErrorHandling(`${API_URL}/sessions`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return res.json();
  }

  async getSessionHistory(id: string): Promise<SessionHistoryResponse> {
    const res = await this.fetchWithErrorHandling(`${API_URL}/sessions/${id}/history`);
    return res.json();
  }

  async deleteSession(id: string): Promise<void> {
    await this.fetchWithErrorHandling(`${API_URL}/sessions/${id}`, {
      method: 'DELETE',
    });
  }

  async closeSession(id: string): Promise<void> {
    await this.fetchWithErrorHandling(`${API_URL}/sessions/${id}/close`, {
      method: 'POST',
    });
  }

  async resumeSession(id: string, initialMessage?: string): Promise<SessionResponse> {
    const body: ResumeSessionRequest = initialMessage ? { initial_message: initialMessage } : {};
    const res = await this.fetchWithErrorHandling(`${API_URL}/sessions/${id}/resume`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return res.json();
  }

  async updateSession(id: string, data: { name?: string | null }): Promise<SessionInfo> {
    const res = await this.fetchWithErrorHandling(`${API_URL}/sessions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return res.json();
  }

  async batchDeleteSessions(sessionIds: string[]): Promise<void> {
    await this.fetchWithErrorHandling(`${API_URL}/sessions/batch-delete`, {
      method: 'POST',
      body: JSON.stringify({ session_ids: sessionIds }),
    });
  }

  async searchSessions(query: string, maxResults: number = 20): Promise<SearchResponse> {
    const params = new URLSearchParams({
      query: query.trim(),
      max_results: maxResults.toString()
    });

    const res = await this.fetchWithErrorHandling(
      `${API_URL}/sessions/search?${params}`
    );
    return res.json();
  }
}

export const apiClient = new ApiClient();
