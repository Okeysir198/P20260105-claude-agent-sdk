import { WS_URL, RECONNECT_DELAY, MAX_RECONNECT_ATTEMPTS } from './constants';
import { tokenService } from './auth';
import type { WebSocketEvent, ClientMessage, UserAnswerMessage } from '@/types';

type EventCallback = (event: WebSocketEvent) => void;
type ErrorCallback = (error: Error) => void;
type StatusCallback = (status: 'connecting' | 'connected' | 'disconnected') => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private onMessageCallbacks: Set<EventCallback> = new Set();
  private onErrorCallbacks: Set<ErrorCallback> = new Set();
  private onStatusCallbacks: Set<StatusCallback> = new Set();
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private connectTimeout: NodeJS.Timeout | null = null; // Track pending connection attempts
  private agentId: string | null = null;
  private sessionId: string | null = null;
  private manualClose = false;
  private connectionId = 0; // Track current connection to prevent stale handlers from triggering
  private pendingAgentId: string | null = null; // Track pending agent for connection
  private pendingSessionId: string | null = null; // Track pending session for connection

  connect(agentId: string | null = null, sessionId: string | null = null) {
    // If already connected/connecting to the same agent and session, ignore
    if ((this.ws && this.ws.readyState === WebSocket.OPEN) &&
        this.agentId === agentId &&
        this.sessionId === sessionId) {
      console.log('Already connected to the same agent/session, ignoring duplicate connect call');
      return;
    }

    // If currently connecting to the same agent/session, ignore
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING &&
        this.pendingAgentId === agentId &&
        this.pendingSessionId === sessionId) {
      console.log('Already connecting to the same agent/session, ignoring duplicate connect call');
      return;
    }

    // Cancel any pending connection attempt
    if (this.connectTimeout) {
      console.log('Cancelling pending connection attempt');
      clearTimeout(this.connectTimeout);
      this.connectTimeout = null;
    }

    // Disconnect existing connection before establishing a new one
    // Only close if we're switching to a different agent/session or if the connection is stale
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      const isDifferentAgent = this.agentId !== agentId || this.sessionId !== sessionId;

      if (isDifferentAgent) {
        console.log('Switching agents/sessions, closing existing connection...');
        this.manualClose = true;
        this.connectionId++; // Increment to invalidate old connection's handlers
        this.ws.close();
        this.ws = null;

        // Delay to allow backend to clean up the old connection
        // This helps prevent race conditions when switching agents rapidly
        this.connectTimeout = setTimeout(() => {
          this.connectTimeout = null;
          this._doConnect(agentId, sessionId);
        }, 500);
        return;
      } else {
        // Same agent/session but connection is in a bad state, let it complete or fail
        console.log('Connection already in progress, waiting for existing connection to complete');
        return;
      }
    }

    this._doConnect(agentId, sessionId);
  }

  private async _doConnect(agentId: string | null = null, sessionId: string | null = null) {
    this.pendingAgentId = agentId;
    this.pendingSessionId = sessionId;
    this.manualClose = false;

    const wsUrl = new URL(WS_URL);

    // Get JWT token for WebSocket authentication
    const accessToken = await tokenService.getAccessToken();
    if (!accessToken) {
      console.error('No JWT token available. Token fetch required.');
      this.notifyStatus('disconnected');
      return;
    }

    wsUrl.searchParams.set('token', accessToken);
    console.log('Using JWT token for WebSocket authentication');

    if (agentId) wsUrl.searchParams.set('agent_id', agentId);
    if (sessionId) wsUrl.searchParams.set('session_id', sessionId);

    const fullUrl = wsUrl.toString();
    // Don't log the token in production
    console.log('Connecting to WebSocket:', fullUrl.replace(/token=[^&]+/, 'token=***'));

    this.notifyStatus('connecting');
    this.ws = new WebSocket(fullUrl);

    // Capture current connectionId for this connection's handlers
    const currentConnectionId = this.connectionId;

    this.ws.onopen = () => {
      console.log('WebSocket connected successfully');
      this.agentId = this.pendingAgentId;
      this.sessionId = this.pendingSessionId;
      this.reconnectAttempts = 0;
      this.notifyStatus('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);
        this.onMessageCallbacks.forEach(cb => cb(data));
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    this.ws.onerror = (error) => {
      // Only log if this is the current connection (not a stale one)
      if (currentConnectionId === this.connectionId) {
        console.warn('WebSocket connection error:', {
          type: error.type,
          target: error.target === this.ws ? this.ws?.readyState : 'stale',
          url: fullUrl.replace(/api_key=[^&]+/, 'api_key=***')
        });
      }
      this.onErrorCallbacks.forEach(cb => cb(new Error('WebSocket connection failed')));
    };

    this.ws.onclose = async (event) => {
      // Ignore close event if it's from a stale connection
      if (currentConnectionId !== this.connectionId) {
        console.log('Ignoring close event from stale connection');
        return;
      }

      console.log('WebSocket closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      this.notifyStatus('disconnected');

      // Check if this was an auth failure (code 1008 = Policy Violation, used for auth errors)
      // Also check reason for "expired", "invalid", or "JWT" keywords
      const isAuthFailure = event.code === 1008 ||
        (event.reason && (
          event.reason.toLowerCase().includes('expired') ||
          event.reason.toLowerCase().includes('invalid') ||
          event.reason.toLowerCase().includes('jwt') ||
          event.reason.toLowerCase().includes('token')
        ));

      if (isAuthFailure) {
        console.log('Token expired, attempting to refresh...');

        // Try to refresh token first
        try {
          const newToken = await tokenService.refreshToken();
          if (newToken) {
            console.log('Token refresh successful');
          } else {
            // Refresh failed, fetch new tokens
            console.log('Token refresh failed, fetching new tokens...');
            await tokenService.fetchTokens();
            console.log('New tokens obtained');
          }
        } catch (err) {
          console.error('Failed to obtain new tokens:', err);
          // Don't reconnect if token fetch failed
          return;
        }
      }

      if (!this.manualClose && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        this.reconnectAttempts++;
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);

        this.reconnectTimeout = setTimeout(() => {
          // Use pendingAgentId/pendingSessionId for reconnection
          // These are set at connection start, while agentId/sessionId are only set on successful open
          this.connect(this.pendingAgentId, this.pendingSessionId);
        }, RECONNECT_DELAY);
      }
    };
  }

  sendMessage(content: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message: ClientMessage = { content };
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  sendAnswer(questionId: string, answers: Record<string, string | string[]>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message: UserAnswerMessage = {
        type: 'user_answer',
        question_id: questionId,
        answers
      };
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  disconnect() {
    this.manualClose = true;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.connectTimeout) {
      clearTimeout(this.connectTimeout);
      this.connectTimeout = null;
    }
    this.ws?.close();
    this.ws = null;
    this.pendingAgentId = null;
    this.pendingSessionId = null;
  }

  onMessage(callback: EventCallback): () => void {
    this.onMessageCallbacks.add(callback);
    return () => this.onMessageCallbacks.delete(callback);
  }

  onError(callback: ErrorCallback): () => void {
    this.onErrorCallbacks.add(callback);
    return () => this.onErrorCallbacks.delete(callback);
  }

  onStatus(callback: StatusCallback): () => void {
    this.onStatusCallbacks.add(callback);
    return () => this.onStatusCallbacks.delete(callback);
  }

  private notifyStatus(status: 'connecting' | 'connected' | 'disconnected') {
    this.onStatusCallbacks.forEach(cb => cb(status));
  }

  getReadyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}
