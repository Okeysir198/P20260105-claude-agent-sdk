import { API_URL, API_KEY } from './constants';
import type {
  AgentInfo,
  SessionInfo,
  SessionResponse,
  SessionHistoryResponse,
  CreateSessionRequest,
  ResumeSessionRequest
} from '@/types';

class ApiClient {
  private get headers() {
    return {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    };
  }

  private async fetchWithErrorHandling(url: string, options?: RequestInit) {
    const response = await fetch(url, {
      ...options,
      headers: { ...this.headers, ...options?.headers },
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
}

export const apiClient = new ApiClient();
