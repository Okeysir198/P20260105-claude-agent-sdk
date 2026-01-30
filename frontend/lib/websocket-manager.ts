import { WS_URL, RECONNECT_DELAY, MAX_RECONNECT_ATTEMPTS } from './constants';
import { tokenService } from './auth';
import { useMessageQueueStore } from '@/lib/store/message-queue-store';
import type { WebSocketEvent, ClientMessage, UserAnswerMessage, PlanApprovalMessage, AuthMessage } from '@/types';
import { getTabBroadcastChannel, TabMessage } from './broadcast-channel';

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
  private isConnecting = false; // Flag to track if connection is in progress (including async token fetch)
  private isAuthenticated = false; // Track if authentication has completed
  private authTimeout: NodeJS.Timeout | null = null; // Track authentication timeout
  // TODO: messageBuffer is reserved for future implementation of message buffering during auth
  private _messageBuffer: string[] = []; // Buffer messages until authenticated
  private static readonly AUTH_TIMEOUT_MS = 5000; // 5 seconds to authenticate

  // Cross-tab sync
  private tabChannel = getTabBroadcastChannel();
  private isFollower: boolean = !this.tabChannel.getIsLeader();
  private unregisterTabListener: (() => void) | null = null;

  constructor() {
    // Listen for tab leader changes
    this.tabChannel.onLeaderChange((isLeader) => {
      const wasFollower = this.isFollower;
      this.isFollower = !isLeader;

      console.log(`[WebSocketManager] Tab leader changed. isLeader: ${isLeader}, isFollower: ${this.isFollower}`);

      // If we became leader and have a pending connection, initiate it
      if (!this.isFollower && wasFollower && this.pendingAgentId) {
        console.log('[WebSocketManager] Became leader, initiating pending connection');
        this._doConnect(this.pendingAgentId, this.pendingSessionId);
      }

      // If we became follower, close any existing connection
      if (this.isFollower && !wasFollower && this.ws) {
        console.log('[WebSocketManager] Became follower, closing existing connection');
        this.manualClose = true;
        this.ws.close();
        this.ws = null;
        this.notifyStatus('disconnected');
      }
    });

    // Listen for messages from leader tab (if we're a follower)
    this.unregisterTabListener = this.tabChannel.onMessage((message: TabMessage) => {
      if (this.isFollower && message.type === 'new-message' && message.message) {
        // Forward message from leader to local callbacks
        this.onMessageCallbacks.forEach(cb => cb(message.message));
      }
    });
  }

  connect(agentId: string | null = null, sessionId: string | null = null) {
    // If we're a follower, don't connect - just store the pending connection params
    // The leader tab will handle the actual connection
    if (this.isFollower) {
      console.log('[WebSocketManager] Follower mode: storing pending connection, not connecting');
      this.pendingAgentId = agentId;
      this.pendingSessionId = sessionId;
      // Request state sync from leader
      this.tabChannel.requestSync();
      return;
    }

    // If already connected/connecting to the same agent and session, ignore
    if ((this.ws && this.ws.readyState === WebSocket.OPEN) &&
        this.agentId === agentId &&
        this.sessionId === sessionId) {
      console.log('Already connected to the same agent/session, ignoring duplicate connect call');
      return;
    }

    // If currently connecting to the same agent/session, ignore
    // This covers both WebSocket CONNECTING state AND async token fetch phase
    if ((this.isConnecting || (this.ws && this.ws.readyState === WebSocket.CONNECTING)) &&
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
    this.isConnecting = true; // Mark connection in progress (including async token fetch)
    this.isAuthenticated = false; // Reset authentication state
    this._messageBuffer = []; // Clear message buffer

    const wsUrl = new URL(WS_URL);

    // Get JWT token for WebSocket authentication (will be sent after connection)
    let accessToken = await tokenService.getAccessToken();
    if (!accessToken) {
      // Try to fetch tokens if not available
      console.log('No JWT token available, fetching tokens...');
      try {
        await tokenService.fetchTokens();
        accessToken = await tokenService.getAccessToken();
      } catch (err) {
        console.error('Failed to fetch JWT tokens:', err);
      }

      if (!accessToken) {
        console.error('Failed to obtain JWT token for WebSocket');
        this.isConnecting = false; // Clear flag on failure
        this.notifyStatus('disconnected');
        return;
      }
    }

    // Note: Token is NOT added to query string for security
    // It will be sent via message after connection established
    console.log('JWT token obtained for post-connect authentication');

    if (agentId) wsUrl.searchParams.set('agent_id', agentId);
    if (sessionId) wsUrl.searchParams.set('session_id', sessionId);

    const fullUrl = wsUrl.toString();
    console.log('Connecting to WebSocket:', fullUrl);

    this.notifyStatus('connecting');
    this.ws = new WebSocket(fullUrl);
    this.isConnecting = false; // WebSocket object created, async phase complete

    // Capture current connectionId for this connection's handlers
    const currentConnectionId = this.connectionId;

    // Capture the token for use in the onopen callback
    // We've already validated that accessToken is not null above
    const tokenToSend = accessToken!;

    this.ws.onopen = () => {
      console.log('WebSocket connected successfully, authenticating...');
      // Send authentication message immediately after connection
      this.authenticate(tokenToSend);
    };

    this.ws.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);

        // Handle authenticated event internally
        if (data.type === 'authenticated') {
          this.handleAuthenticated();
        }

        // Broadcast to all tabs (if we're leader)
        if (!this.isFollower) {
          this.tabChannel.broadcastMessage(data);
        }

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

      // Handle specific close codes with appropriate recovery actions
      // 4005 = TOKEN_EXPIRED, 4006 = TOKEN_INVALID
      const isTokenExpired = event.code === 4005 || event.code === 4006;
      // 4004 = SESSION_NOT_FOUND
      const isSessionNotFound = event.code === 4004;
      // 4007 = RATE_LIMITED
      const isRateLimited = event.code === 4007;
      // 4008 = AGENT_NOT_FOUND
      const isAgentNotFound = event.code === 4008;

      if (isTokenExpired) {
        console.log('Token expired/invalid, attempting to refresh...');

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
      } else if (isSessionNotFound) {
        console.log('Session not found, will start new session on reconnect');
        // Clear session ID so next connect starts fresh
        this.sessionId = null;
        this.pendingSessionId = null;
      } else if (isRateLimited) {
        console.log('Rate limited, backing off before reconnect');
        // Use longer delay for rate limiting
        if (!this.manualClose && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          this.reconnectAttempts++;
          const backoffDelay = RECONNECT_DELAY * Math.pow(2, this.reconnectAttempts - 1);
          console.log(`Reconnecting after ${backoffDelay}ms... Attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);

          this.reconnectTimeout = setTimeout(() => {
            this.connect(this.pendingAgentId, this.pendingSessionId);
          }, backoffDelay);
        }
        return;
      } else if (isAgentNotFound) {
        console.error('Agent not found, not reconnecting');
        return;
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
      console.warn('WebSocket is not connected, queuing message');
      // Enqueue message when disconnected
      useMessageQueueStore.getState().enqueueMessage(content);
    }
  }

  flushQueue() {
    const queuedMessages = useMessageQueueStore.getState().getQueuedMessages();
    if (queuedMessages.length === 0) {
      return;
    }

    console.log(`Flushing ${queuedMessages.length} queued messages`);

    // Send all queued messages
    queuedMessages.forEach((queuedMessage) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        const message: ClientMessage = { content: queuedMessage.content };
        this.ws.send(JSON.stringify(message));
        // Remove from queue after sending
        useMessageQueueStore.getState().dequeueMessage(queuedMessage.id);
      }
    });
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

  sendPlanApproval(planId: string, approved: boolean, feedback?: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message: PlanApprovalMessage = {
        type: 'plan_approval_response',
        plan_id: planId,
        approved,
        feedback
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

  forceReconnect(agentId: string | null = null, sessionId: string | null = null) {
    // Cancel pending connection attempts
    if (this.connectTimeout) {
      clearTimeout(this.connectTimeout);
      this.connectTimeout = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    // Increment connection ID to invalidate stale handlers
    this.connectionId++;

    // Close existing connection immediately
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.manualClose = true;
      this.ws.close();
      this.ws = null;
    }

    // Reset stored agent/session IDs to avoid deduplication
    this.agentId = null;
    this.sessionId = null;

    // Connect immediately without delay
    this._doConnect(agentId, sessionId);
  }

  private authenticate(token: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('Cannot authenticate: WebSocket is not open');
      return;
    }

    const authMessage: AuthMessage = {
      type: 'auth',
      token
    };

    this.ws.send(JSON.stringify(authMessage));
    console.log('Authentication message sent');

    // Set timeout for authentication
    this.authTimeout = setTimeout(() => {
      if (!this.isAuthenticated) {
        console.error('Authentication timeout');
        this.ws?.close();
      }
    }, WebSocketManager.AUTH_TIMEOUT_MS);
  }

  private handleAuthenticated() {
    console.log('Authentication successful');
    this.isAuthenticated = true;

    // Clear auth timeout
    if (this.authTimeout) {
      clearTimeout(this.authTimeout);
      this.authTimeout = null;
    }

    // Set connection status to connected
    this.agentId = this.pendingAgentId;
    this.sessionId = this.pendingSessionId;
    this.reconnectAttempts = 0;
    this.notifyStatus('connected');

    // Flush any queued messages
    this.flushQueue();
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
