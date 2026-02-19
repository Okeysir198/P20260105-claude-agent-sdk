'use client';

import { useChat } from '@/hooks/use-chat';
import { useHistoryLoading } from '@/hooks/use-history-loading';
import { useConnectionTracking } from '@/hooks/use-connection-tracking';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { QuestionModal } from './question-modal';
import { PlanApprovalModal } from './plan-approval-modal';
import { KanbanSync } from '@/components/kanban';
import { ConnectionBanner } from './connection-banner';
import { ConnectionError } from './connection-error';
import { InitialLoading } from './initial-loading';
import { HistoryLoadError } from './history-load-error';
import { useChatStore } from '@/lib/store/chat-store';
import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
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

const MAX_HISTORY_RETRIES = 3;

// =============================================================================
// Main Chat Container Component
// =============================================================================

function ChatContainerInner() {
  const {
    sendMessage,
    sendAnswer,
    sendPlanApproval,
    cancelStream,
    compactContext,
  } = useChat();

  const connectionStatus = useChatStore((s) => s.connectionStatus);
  const sessionId = useChatStore((s) => s.sessionId);
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const isCancelling = useChatStore((s) => s.isCancelling);
  const isCompacting = useChatStore((s) => s.isCompacting);

  const { historyError, historyRetryCount, isLoadingHistory, handleHistoryRetry } = useHistoryLoading();
  const { wasConnected, reconnectAttempt, isReconnecting, handleManualReconnect } = useConnectionTracking();

  // Connection error state
  if (connectionStatus === 'error') {
    return <ConnectionError onRetry={handleManualReconnect} />;
  }

  // Initial loading state (only when first connecting, not reconnecting)
  if ((connectionStatus === 'connecting' || connectionStatus === 'disconnected') && !wasConnected) {
    return <InitialLoading status={connectionStatus} />;
  }

  // At this point, connectionStatus is not 'error' and not initial loading
  // so it must be 'connected', 'connecting', or 'disconnected' with wasConnected=true
  const showConnectionBanner = connectionStatus !== 'connected';

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
          onCancel={cancelStream}
          onCompact={compactContext}
          isStreaming={isStreaming}
          isCancelling={isCancelling}
          isCompacting={isCompacting}
          canCompact={!!sessionId && messages.length > 0}
          disabled={connectionStatus !== 'connected'}
        />
      </div>

      <QuestionModal onSubmit={sendAnswer} />
      <PlanApprovalModal onSubmit={sendPlanApproval} />
      <KanbanSync />
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
