'use client';
import { useChat } from '@/hooks/use-chat';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { QuestionModal } from './question-modal';
import { PlanApprovalModal } from './plan-approval-modal';
import { useChatStore } from '@/lib/store/chat-store';
import { useEffect, useRef, useCallback, useState, Component, type ReactNode } from 'react';
import { apiClient } from '@/lib/api-client';
import { Loader2, WifiOff, RefreshCw, AlertTriangle } from 'lucide-react';
import { convertHistoryToChatMessages } from '@/lib/history-utils';
import { Button } from '@/components/ui/button';
import { MAX_RECONNECT_ATTEMPTS } from '@/lib/constants';

// =============================================================================
// Error Boundary Component
// =============================================================================

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ChatErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Chat container error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-8 w-8" />
            <h2 className="text-lg font-semibold">Something went wrong</h2>
          </div>
          <p className="max-w-md text-center text-sm text-muted-foreground">
            We encountered an unexpected error while displaying the chat.
            This might be a temporary issue.
          </p>
          <div className="flex gap-2">
            <Button variant="outline" onClick={this.handleRetry}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
            <Button variant="ghost" onClick={() => window.location.reload()}>
              Reload Page
            </Button>
          </div>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="mt-4 max-w-lg rounded-md border border-destructive/20 bg-destructive/5 p-4 text-xs">
              <summary className="cursor-pointer font-medium text-destructive">
                Error Details (Development Only)
              </summary>
              <pre className="mt-2 overflow-auto whitespace-pre-wrap text-muted-foreground">
                {this.state.error.message}
                {'\n\n'}
                {this.state.error.stack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

// =============================================================================
// Connection Status Banner
// =============================================================================

interface ConnectionBannerProps {
  status: 'connecting' | 'disconnected' | 'reconnecting';
  reconnectAttempt?: number;
  maxAttempts?: number;
  onRetry?: () => void;
}

function ConnectionBanner({ status, reconnectAttempt, maxAttempts, onRetry }: ConnectionBannerProps) {
  const getMessage = () => {
    switch (status) {
      case 'connecting':
        return 'Connecting to server...';
      case 'reconnecting':
        return reconnectAttempt && maxAttempts
          ? `Connection lost. Reconnecting (${reconnectAttempt}/${maxAttempts})...`
          : 'Connection lost. Reconnecting...';
      case 'disconnected':
        return 'You are currently offline';
      default:
        return 'Connection issue detected';
    }
  };

  const getIcon = () => {
    if (status === 'disconnected') {
      return <WifiOff className="h-4 w-4" />;
    }
    return <Loader2 className="h-4 w-4 animate-spin" />;
  };

  return (
    <div className="flex items-center justify-between gap-3 border-b border-yellow-500/30 bg-yellow-500/10 px-4 py-2 text-sm text-yellow-700 dark:text-yellow-400">
      <div className="flex items-center gap-2">
        {getIcon()}
        <span>{getMessage()}</span>
      </div>
      {status === 'disconnected' && onRetry && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onRetry}
          className="h-7 px-2 text-yellow-700 hover:text-yellow-800 dark:text-yellow-400 dark:hover:text-yellow-300"
        >
          <RefreshCw className="mr-1 h-3 w-3" />
          Retry
        </Button>
      )}
    </div>
  );
}

// =============================================================================
// History Loading Error Component
// =============================================================================

interface HistoryLoadErrorProps {
  error: string;
  retryCount: number;
  maxRetries: number;
  isRetrying: boolean;
  onRetry: () => void;
}

function HistoryLoadError({ error, retryCount, maxRetries, isRetrying, onRetry }: HistoryLoadErrorProps) {
  const canRetry = retryCount < maxRetries;

  return (
    <div className="mx-4 my-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
        <div className="flex-1 space-y-2">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
            Unable to load chat history
          </p>
          <p className="text-xs text-amber-700 dark:text-amber-300">
            {getUserFriendlyErrorMessage(error)}
          </p>
          {canRetry && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              disabled={isRetrying}
              className="mt-2 border-amber-500/30 text-amber-700 hover:bg-amber-500/10 dark:text-amber-300"
            >
              {isRetrying ? (
                <>
                  <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-3 w-3" />
                  Retry ({retryCount + 1}/{maxRetries})
                </>
              )}
            </Button>
          )}
          {!canRetry && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Maximum retry attempts reached. You can continue chatting, but previous messages may not be visible.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Convert technical error messages to user-friendly ones
 */
function getUserFriendlyErrorMessage(error: string): string {
  const errorLower = error.toLowerCase();

  if (errorLower.includes('network') || errorLower.includes('fetch')) {
    return 'Unable to connect to the server. Please check your internet connection.';
  }

  if (errorLower.includes('timeout')) {
    return 'The request took too long. The server might be busy.';
  }

  if (errorLower.includes('401') || errorLower.includes('unauthorized')) {
    return 'Your session has expired. Please refresh the page to log in again.';
  }

  if (errorLower.includes('403') || errorLower.includes('forbidden')) {
    return 'You do not have permission to access this resource.';
  }

  if (errorLower.includes('404') || errorLower.includes('not found')) {
    return 'The requested resource could not be found. It may have been deleted.';
  }

  if (errorLower.includes('500') || errorLower.includes('server error')) {
    return 'The server encountered an error. Please try again later.';
  }

  if (errorLower.includes('websocket') || errorLower.includes('connection')) {
    return 'Connection to the chat server was interrupted. Attempting to reconnect...';
  }

  // Default message
  return 'An unexpected error occurred. Please try again.';
}

/**
 * Get user-friendly connection error message
 */
function getConnectionErrorMessage(): string {
  return 'Unable to establish a connection to the chat server. This could be due to network issues or the server being temporarily unavailable.';
}

// =============================================================================
// Main Chat Container Component
// =============================================================================

const MAX_HISTORY_RETRIES = 3;

function ChatContainerInner() {
  const { sendMessage, sendAnswer, sendPlanApproval, status } = useChat();
  const connectionStatus = useChatStore((s) => s.connectionStatus);
  const sessionId = useChatStore((s) => s.sessionId);
  const agentId = useChatStore((s) => s.agentId);
  const messages = useChatStore((s) => s.messages);
  const setMessages = useChatStore((s) => s.setMessages);

  // History loading state
  const hasLoadedHistory = useRef(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyRetryCount, setHistoryRetryCount] = useState(0);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Connection state tracking
  const [wasConnected, setWasConnected] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  // Handler for question modal answer submission
  const handleQuestionAnswer = useCallback((questionId: string, answers: Record<string, string | string[]>) => {
    sendAnswer(questionId, answers);
  }, [sendAnswer]);

  // Handler for plan approval modal submission
  const handlePlanApproval = useCallback((planId: string, approved: boolean, feedback?: string) => {
    sendPlanApproval(planId, approved, feedback);
  }, [sendPlanApproval]);

  // Track connection state changes for reconnection UI
  useEffect(() => {
    if (connectionStatus === 'connected') {
      setWasConnected(true);
      setReconnectAttempt(0);
    } else if (connectionStatus === 'connecting' && wasConnected) {
      setReconnectAttempt((prev) => prev + 1);
    }
  }, [connectionStatus, wasConnected]);

  // Load session history with retry logic
  const loadHistory = useCallback(async () => {
    if (!sessionId || isLoadingHistory) return;

    setIsLoadingHistory(true);
    setHistoryError(null);

    try {
      const historyData = await apiClient.getSessionHistory(sessionId);
      const chatMessages = convertHistoryToChatMessages(historyData.messages);

      if (chatMessages.length > 0) {
        setMessages(chatMessages);
      }
      hasLoadedHistory.current = true;
      setHistoryRetryCount(0);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to load session history:', error);
      setHistoryError(errorMessage);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [sessionId, isLoadingHistory, setMessages]);

  // Retry handler for history loading
  const handleHistoryRetry = useCallback(() => {
    if (historyRetryCount < MAX_HISTORY_RETRIES) {
      setHistoryRetryCount((prev) => prev + 1);
      loadHistory();
    }
  }, [historyRetryCount, loadHistory]);

  // Manual reconnection handler
  const handleManualReconnect = useCallback(() => {
    window.location.reload();
  }, []);

  // Reset history loaded flag when session changes
  // NOTE: This effect must come BEFORE the load effect to ensure proper ordering
  useEffect(() => {
    // Only reset if there are no messages (messages may have been loaded by SessionItem)
    // This prevents unnecessary history loads when clicking on a session
    if (messages.length === 0) {
      hasLoadedHistory.current = false;
    }
    setHistoryError(null);
    setHistoryRetryCount(0);
  }, [sessionId, messages.length]);

  // Load session history on mount when there's a sessionId but no messages
  useEffect(() => {
    if (sessionId && !hasLoadedHistory.current && messages.length === 0) {
      loadHistory();
    }
  }, [sessionId, messages.length, loadHistory]);

  // Determine if we should show the connection banner
  const showConnectionBanner = connectionStatus !== 'connected' && connectionStatus !== 'error';
  const isReconnecting = wasConnected && connectionStatus === 'connecting';

  if (connectionStatus === 'error') {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
        <div className="flex items-center gap-2 text-destructive">
          <WifiOff className="h-8 w-8" />
          <h2 className="text-lg font-semibold">Connection Error</h2>
        </div>
        <p className="max-w-md text-center text-sm text-muted-foreground">
          {getConnectionErrorMessage()}
        </p>
        <div className="flex flex-col items-center gap-2">
          <Button onClick={handleManualReconnect}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Reconnect
          </Button>
          <p className="text-xs text-muted-foreground">
            If the problem persists, try refreshing the page or checking your network connection.
          </p>
        </div>
      </div>
    );
  }

  // Show loading state only when first connecting (not reconnecting)
  if ((connectionStatus === 'connecting' || connectionStatus === 'disconnected') && !wasConnected) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">
          {connectionStatus === 'connecting' ? 'Connecting to server...' : 'Waiting for connection...'}
        </p>
        {connectionStatus === 'disconnected' && (
          <Button variant="outline" size="sm" onClick={handleManualReconnect}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry Connection
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Connection status banner for reconnecting state */}
      {showConnectionBanner && wasConnected && (
        <ConnectionBanner
          status={isReconnecting ? 'reconnecting' : 'disconnected'}
          reconnectAttempt={reconnectAttempt}
          maxAttempts={MAX_RECONNECT_ATTEMPTS}
          onRetry={handleManualReconnect}
        />
      )}

      {/* History loading error notification */}
      {historyError && (
        <HistoryLoadError
          error={historyError}
          retryCount={historyRetryCount}
          maxRetries={MAX_HISTORY_RETRIES}
          isRetrying={isLoadingHistory}
          onRetry={handleHistoryRetry}
        />
      )}

      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      <div className="shrink-0">
        <ChatInput
          onSend={sendMessage}
          disabled={connectionStatus !== 'connected'}
        />
      </div>
      <QuestionModal onSubmit={handleQuestionAnswer} />
      <PlanApprovalModal onSubmit={handlePlanApproval} />
    </div>
  );
}

// =============================================================================
// Exported Component with Error Boundary
// =============================================================================

export function ChatContainer() {
  return (
    <ChatErrorBoundary>
      <ChatContainerInner />
    </ChatErrorBoundary>
  );
}
