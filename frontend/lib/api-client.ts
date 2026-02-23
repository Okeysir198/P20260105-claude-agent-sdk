import { API_URL } from './constants';
import type {
  AgentInfo,
  SessionInfo,
  SessionResponse,
  SessionHistoryResponse,
  CreateSessionRequest,
  ResumeSessionRequest,
  SearchResponse,
  FileUploadResponse,
  FileListResponse,
  FileDeleteResponse
} from '@/types';

function extractErrorMessage(body: Record<string, unknown>, fallback: string): string {
  if (typeof body.error === 'string') return body.error;

  const detail = body.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === 'object' && d && 'msg' in d ? (d as { msg: string }).msg : JSON.stringify(d)))
      .join('; ');
  }

  return fallback;
}

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
      const body = await response.json().catch(() => ({}));
      throw new Error(extractErrorMessage(body, `Request failed (${response.status})`));
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

  async uploadFile(
    sessionId: string,
    file: File,
    onProgress?: (progress: number) => void,
    cwdId?: string,
  ): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (cwdId) {
      formData.append('cwd_id', cwdId);
    } else {
      formData.append('session_id', sessionId);
    }

    return new Promise<FileUploadResponse>((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            onProgress(Math.round((event.loaded / event.total) * 100));
          }
        });
      }

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText) as FileUploadResponse);
          } catch {
            reject(new Error('Failed to parse upload response'));
          }
        } else {
          try {
            const body = JSON.parse(xhr.responseText);
            reject(new Error(extractErrorMessage(body, `Upload failed (${xhr.status})`)));
          } catch {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
      xhr.addEventListener('abort', () => reject(new Error('Upload aborted')));

      xhr.open('POST', '/api/files/upload');
      xhr.send(formData);
    });
  }

  async listFiles(sessionId: string, fileType?: 'input' | 'output'): Promise<FileListResponse> {
    const params = new URLSearchParams();
    if (fileType) {
      params.append('file_type', fileType);
    }

    const url = params.toString()
      ? `${API_URL}/files/${encodeURIComponent(sessionId)}/list?${params}`
      : `${API_URL}/files/${encodeURIComponent(sessionId)}/list`;

    const res = await this.fetchWithErrorHandling(url);
    return res.json();
  }

  async downloadFile(
    sessionId: string,
    fileType: 'input' | 'output',
    safeName: string
  ): Promise<Blob> {
    const url = `${API_URL}/files/${encodeURIComponent(sessionId)}/download/${fileType}/${encodeURIComponent(safeName)}`;

    const response = await fetch(url);

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(extractErrorMessage(body, `Download failed (${response.status})`));
    }

    return response.blob();
  }

  async deleteFile(
    sessionId: string,
    safeName: string,
    fileType: 'input' | 'output'
  ): Promise<FileDeleteResponse> {
    const res = await this.fetchWithErrorHandling(`${API_URL}/files/${encodeURIComponent(sessionId)}/delete`, {
      method: 'DELETE',
      body: JSON.stringify({
        safe_name: safeName,
        file_type: fileType,
      }),
    });
    return res.json();
  }
}

export const apiClient = new ApiClient();
