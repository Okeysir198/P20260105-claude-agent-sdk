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

  /**
   * Upload a file to a session.
   * @param sessionId - Session identifier
   * @param file - File to upload
   * @param onProgress - Optional callback for upload progress (0-100)
   * @returns Upload response with file metadata
   */
  async uploadFile(
    sessionId: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    const xhr = new XMLHttpRequest();

    return new Promise<FileUploadResponse>((resolve, reject) => {
      // Track upload progress if callback provided
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            onProgress(progress);
          }
        });
      }

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText) as FileUploadResponse;
            resolve(response);
          } catch (error) {
            reject(new Error('Failed to parse upload response'));
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.error || error.detail || 'Upload failed'));
          } catch {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload aborted'));
      });

      xhr.open('POST', `${API_URL}/files/upload`);
      xhr.send(formData);
    });
  }

  /**
   * List files for a session.
   * @param sessionId - Session identifier
   * @param fileType - Optional file type filter ('input' or 'output')
   * @returns List of files
   */
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

  /**
   * Download a file from a session.
   * @param sessionId - Session identifier
   * @param fileType - 'input' or 'output'
   * @param safeName - Safe filename
   * @returns File blob for download
   */
  async downloadFile(
    sessionId: string,
    fileType: 'input' | 'output',
    safeName: string
  ): Promise<Blob> {
    const url = `${API_URL}/files/${encodeURIComponent(sessionId)}/download/${fileType}/${encodeURIComponent(safeName)}`;

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || error.detail || 'Download failed');
    }

    return response.blob();
  }

  /**
   * Delete a file from a session.
   * @param sessionId - Session identifier
   * @param safeName - Safe filename
   * @param fileType - 'input' or 'output'
   * @returns Delete response
   */
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
