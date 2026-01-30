/**
 * BroadcastChannel for cross-tab communication.
 *
 * This enables multiple browser tabs to coordinate WebSocket connections,
 * ensuring only one tab maintains the actual WebSocket connection (the "leader").
 * Other tabs become "followers" and receive messages via the channel.
 */

export interface TabMessage {
  type: 'leader-election' | 'leader-heartbeat' | 'new-message' | 'sync-state' | 'leader-resign';
  tabId: string;
  timestamp: number;
  // For leader-election
  isLeader?: boolean;
  // For new-message
  message?: any;
  // For sync-state
  state?: {
    sessionId: string | null;
    agentId: string | null;
    messages: any[];
    connectionStatus: string;
  };
}

const CHANNEL_NAME = 'claude-agent-sdk-chat';

export class TabBroadcastChannel {
  private channel: BroadcastChannel;
  private tabId: string;
  private isLeader: boolean = false;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private listeners: Set<(message: TabMessage) => void> = new Set();
  private onLeaderChangeCallback: ((isLeader: boolean) => void) | null = null;

  constructor() {
    this.channel = new BroadcastChannel(CHANNEL_NAME);
    this.tabId = `tab-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

    // Listen for messages from other tabs
    this.channel.onmessage = (event) => {
      this.handleMessage(event.data);
    };

    // Start leader election
    this.startLeaderElection();
  }

  /**
   * Get this tab's unique identifier
   */
  getTabId(): string {
    return this.tabId;
  }

  /**
   * Check if this tab is the leader
   */
  getIsLeader(): boolean {
    return this.isLeader;
  }

  /**
   * Set callback for leader status changes
   * Returns a cleanup function to remove the callback
   */
  onLeaderChange(callback: (isLeader: boolean) => void): () => void {
    this.onLeaderChangeCallback = callback;
    // Return cleanup function
    return () => {
      this.onLeaderChangeCallback = null;
    };
  }

  /**
   * Register a listener for all tab messages
   */
  onMessage(callback: (message: TabMessage) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  /**
   * Start the leader election process
   */
  private startLeaderElection() {
    // Announce our presence and ask if anyone is already leader
    this.broadcast({
      type: 'leader-election',
      tabId: this.tabId,
      timestamp: Date.now(),
    });

    // If no response within 100ms, we become leader
    setTimeout(() => {
      if (!this.isLeader) {
        this.becomeLeader();
      }
    }, 100);
  }

  /**
   * Handle incoming messages from other tabs
   */
  private handleMessage(message: TabMessage) {
    // Ignore messages from ourselves
    if (message.tabId === this.tabId) {
      return;
    }

    switch (message.type) {
      case 'leader-election':
        // If we're leader, respond to let them know
        if (this.isLeader) {
          this.broadcast({
            type: 'leader-heartbeat',
            tabId: this.tabId,
            timestamp: Date.now(),
            isLeader: true,
          });
        }
        break;

      case 'leader-heartbeat':
        // Someone else is leader, we remain a follower
        if (message.isLeader && this.isLeader) {
          // We thought we were leader, but someone else is too
          // Use tab ID as tiebreaker (lower ID wins)
          if (message.tabId < this.tabId) {
            this.resignLeadership();
          }
        }
        break;

      case 'leader-resign':
        // Leader is resigning, start election
        if (!this.isLeader) {
          this.startLeaderElection();
        }
        break;

      default:
        // Pass other messages to listeners
        this.listeners.forEach(cb => cb(message));
        break;
    }
  }

  /**
   * Become the leader tab
   */
  private becomeLeader() {
    this.isLeader = true;
    console.log(`[TabSync] Tab ${this.tabId} became leader`);

    // Start heartbeat to maintain leadership
    this.heartbeatInterval = setInterval(() => {
      this.broadcast({
        type: 'leader-heartbeat',
        tabId: this.tabId,
        timestamp: Date.now(),
        isLeader: true,
      });
    }, 1000);

    // Notify callback
    if (this.onLeaderChangeCallback) {
      this.onLeaderChangeCallback(true);
    }
  }

  /**
   * Resign leadership (become a follower)
   */
  private resignLeadership() {
    this.isLeader = false;
    console.log(`[TabSync] Tab ${this.tabId} resigned leadership`);

    // Stop heartbeat
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    // Notify callback
    if (this.onLeaderChangeCallback) {
      this.onLeaderChangeCallback(false);
    }
  }

  /**
   * Broadcast a message to all tabs
   */
  broadcast(message: TabMessage): void {
    this.channel.postMessage(message);
  }

  /**
   * Send a new message to all tabs (called by leader when receiving from WebSocket)
   */
  broadcastMessage(message: any): void {
    this.broadcast({
      type: 'new-message',
      tabId: this.tabId,
      timestamp: Date.now(),
      message,
    });
  }

  /**
   * Request state sync from leader
   */
  requestSync(): void {
    this.broadcast({
      type: 'sync-state',
      tabId: this.tabId,
      timestamp: Date.now(),
    });
  }

  /**
   * Broadcast current state (called by leader)
   */
  broadcastState(state: TabMessage['state']): void {
    this.broadcast({
      type: 'sync-state',
      tabId: this.tabId,
      timestamp: Date.now(),
      state,
    });
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    // If we're leader, resign so another tab can take over
    if (this.isLeader) {
      this.broadcast({
        type: 'leader-resign',
        tabId: this.tabId,
        timestamp: Date.now(),
      });
    }

    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    this.channel.close();
    this.listeners.clear();
  }
}

// Singleton instance
let instance: TabBroadcastChannel | null = null;

export function getTabBroadcastChannel(): TabBroadcastChannel {
  if (!instance) {
    instance = new TabBroadcastChannel();

    // Cleanup on page unload
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => {
        instance?.destroy();
        instance = null;
      });
    }
  }
  return instance;
}
